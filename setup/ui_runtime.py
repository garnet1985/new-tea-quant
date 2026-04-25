from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, Tuple

from core.system import python_minimum, system_meta

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = REPO_ROOT / "core" / "ui"
BFF_ROOT = UI_ROOT / "bff"
FED_ROOT = UI_ROOT / "fed"
STATE_FILE = REPO_ROOT / ".ntq" / "install-state.json"
BFF_REQUIREMENTS = BFF_ROOT / "requirements.txt"
FED_LOCKFILE = FED_ROOT / "package-lock.json"
FED_NODE_MODULES = FED_ROOT / "node_modules"


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_state() -> Dict[str, Any]:
    if not STATE_FILE.is_file():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def check_runtime_prerequisites() -> Tuple[bool, str]:
    py_min = python_minimum()
    if sys.version_info < py_min:
        return False, f"Python 版本过低，当前 {sys.version_info.major}.{sys.version_info.minor}，需要 >= {py_min[0]}.{py_min[1]}"
    if shutil.which("node") is None:
        return False, "未检测到 node，请先安装 Node.js"
    if shutil.which("npm") is None:
        return False, "未检测到 npm，请先安装 npm"
    if not BFF_REQUIREMENTS.is_file():
        return False, f"缺少 BFF 依赖文件: {BFF_REQUIREMENTS}"
    if not (FED_ROOT / "package.json").is_file():
        return False, f"缺少 FED package.json: {FED_ROOT / 'package.json'}"
    return True, "ok"


def needs_install() -> bool:
    state = _load_state()
    if not state:
        return True

    if state.get("coreVersion") != system_meta.version:
        return True

    python_state = state.get("python", {})
    node_state = state.get("node", {})
    if python_state.get("uiRequirementsHash") != _sha256_file(BFF_REQUIREMENTS):
        return True
    if node_state.get("fedLockHash") != _sha256_file(FED_LOCKFILE):
        return True
    if not FED_NODE_MODULES.is_dir():
        return True

    if state.get("setupRuntime", {}).get("lastStatus") != "success":
        return True
    return False


def install_ui_runtime(force: bool = False) -> None:
    if not force and not needs_install():
        print("安装检查通过，跳过依赖安装。", flush=True)
        return

    print("开始安装 UI 最小依赖（BFF + FED）...", flush=True)

    pip_cmd = [sys.executable, "-m", "pip", "install", "--no-compile", "-r", str(BFF_REQUIREMENTS)]
    pip_ret = subprocess.run(pip_cmd, cwd=str(REPO_ROOT))
    if pip_ret.returncode != 0:
        raise RuntimeError("安装 BFF Python 依赖失败")

    npm_cmd = ["npm", "install"]
    npm_ret = subprocess.run(npm_cmd, cwd=str(FED_ROOT))
    if npm_ret.returncode != 0:
        raise RuntimeError("安装 FED Node 依赖失败")

    state = {
        "coreVersion": system_meta.version,
        "python": {
            "uiRequirementsHash": _sha256_file(BFF_REQUIREMENTS),
            "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "node": {
            "fedLockHash": _sha256_file(FED_LOCKFILE),
            "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "setupRuntime": {
            "lastStatus": "success",
            "lastFailedStepId": "",
        },
    }
    _save_state(state)
    print("UI 最小依赖安装完成。", flush=True)


def _wait_bff_ready(host: str, port: int, timeout_sec: int = 30) -> bool:
    url = f"http://{host}:{port}/api/health"
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(1)
    return False


def launch_ui_stack() -> None:
    host = os.getenv("NTQ_BFF_HOST", "127.0.0.1")
    port = int(os.getenv("NTQ_BFF_PORT", "5001"))

    bff_env = os.environ.copy()
    bff_env["NTQ_BFF_HOST"] = host
    bff_env["NTQ_BFF_PORT"] = str(port)
    bff_cmd = [sys.executable, "-m", "core.ui.bff.app"]
    bff_proc = subprocess.Popen(bff_cmd, cwd=str(REPO_ROOT), env=bff_env)

    if not _wait_bff_ready(host, port):
        bff_proc.terminate()
        raise RuntimeError("BFF 启动超时，未通过健康检查 /api/health")

    fed_env = os.environ.copy()
    fed_cmd = ["npm", "start"]
    fed_proc = subprocess.Popen(fed_cmd, cwd=str(FED_ROOT), env=fed_env)

    print("UI 已启动：BFF + FED", flush=True)
    print("FED 默认地址: http://localhost:8888/strategy-workbench", flush=True)
    try:
        webbrowser.open("http://localhost:8888/strategy-workbench")
    except Exception:
        pass
    try:
        fed_proc.wait()
    except KeyboardInterrupt:
        print("\n收到中断，正在关闭服务...", flush=True)
    finally:
        for proc in (fed_proc, bff_proc):
            if proc.poll() is None:
                proc.terminate()
        for proc in (fed_proc, bff_proc):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
