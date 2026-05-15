from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Tuple

from core.system import python_minimum

from setup.install_runtime import (
    REPO_ROOT,
    UI_BFF_REQUIREMENTS,
    UI_FED_LOCKFILE,
    mark_runtime,
    needs_install,
    sha256_file,
)

UI_ROOT = REPO_ROOT / "core" / "ui"
BFF_ROOT = UI_ROOT / "bff"
FED_ROOT = UI_ROOT / "fed"
BFF_REQUIREMENTS = UI_BFF_REQUIREMENTS
FED_LOCKFILE = UI_FED_LOCKFILE
FED_NODE_MODULES = REPO_ROOT / "core" / "ui" / "fed" / "node_modules"


def _bootstrap_pip() -> None:
    """Upgrade pip/setuptools/wheel so dependency resolution matches modern Flask stacks."""
    if os.environ.get("NTQ_SKIP_PIP_BOOTSTRAP", "").strip().lower() in ("1", "true", "yes"):
        return
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if os.environ.get("NTQ_PIP_NO_CACHE", "").strip().lower() in ("1", "true", "yes"):
        cmd.append("--no-cache-dir")
    cmd.extend(["pip>=24.0", "setuptools>=65", "wheel"])
    print("正在升级 pip / setuptools / wheel（缓解依赖解析冲突）...", flush=True)
    ret = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if ret.returncode != 0:
        print("⚠️ pip 自升级失败，将继续尝试安装 BFF 依赖；若仍失败请手动: python -m pip install -U pip", flush=True)


def check_runtime_prerequisites() -> Tuple[bool, str]:
    py_min = python_minimum()
    if sys.version_info < py_min:
        return False, (
            f"Python 版本过低，当前 {sys.version_info.major}.{sys.version_info.minor}，"
            f"需要 >= {py_min[0]}.{py_min[1]}"
        )
    if shutil.which("node") is None:
        return False, "未检测到 node，请先安装 Node.js"
    if shutil.which("npm") is None:
        return False, "未检测到 npm，请先安装 npm"
    if not BFF_REQUIREMENTS.is_file():
        return False, f"缺少 BFF 依赖文件: {BFF_REQUIREMENTS}"
    if not (FED_ROOT / "package.json").is_file():
        return False, f"缺少 FED package.json: {FED_ROOT / 'package.json'}"
    return True, "ok"


def install_ui_runtime(force: bool = False) -> None:
    if not force and not needs_install("ui"):
        print("安装检查通过，跳过依赖安装。", flush=True)
        return

    print("开始安装 UI 最小依赖（BFF + FED）...", flush=True)

    _bootstrap_pip()

    pip_cmd = [sys.executable, "-m", "pip", "install", "--no-compile", "--prefer-binary"]
    if os.environ.get("NTQ_PIP_NO_CACHE", "").strip().lower() in ("1", "true", "yes"):
        pip_cmd.append("--no-cache-dir")
    pip_cmd.extend(["-r", str(BFF_REQUIREMENTS)])
    pip_ret = subprocess.run(pip_cmd, cwd=str(REPO_ROOT))
    if pip_ret.returncode != 0:
        raise RuntimeError("安装 BFF Python 依赖失败")

    npm_cmd = ["npm", "install"]
    npm_ret = subprocess.run(npm_cmd, cwd=str(FED_ROOT))
    if npm_ret.returncode != 0:
        raise RuntimeError("安装 FED Node 依赖失败")

    mark_runtime(
        "ui",
        success=True,
        fingerprints={
            "python": {
                "uiRequirementsHash": sha256_file(BFF_REQUIREMENTS),
                "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            "node": {
                "fedLockHash": sha256_file(FED_LOCKFILE),
                "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        },
    )
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
