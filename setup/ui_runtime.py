from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Tuple

from core.system import python_minimum
from core.ui.ports import BFF_DEFAULT_PORT, FED_DEV_PORT

from setup.install_runtime import (
    REPO_ROOT,
    UI_BFF_REQUIREMENTS,
    UI_FED_BUILD_DIR,
    UI_FED_LOCKFILE,
    UI_FED_ROOT,
    fed_build_fingerprint,
    fed_build_ready,
    mark_runtime,
    needs_install,
    sha256_file,
    ui_dev_mode,
)

FED_ROOT = UI_FED_ROOT
BFF_REQUIREMENTS = UI_BFF_REQUIREMENTS
FED_LOCKFILE = UI_FED_LOCKFILE


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _bootstrap_pip() -> None:
    if _env_truthy("NTQ_SKIP_PIP_BOOTSTRAP"):
        return
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if _env_truthy("NTQ_PIP_NO_CACHE"):
        cmd.append("--no-cache-dir")
    cmd.extend(["pip>=24.0", "setuptools>=65", "wheel"])
    print("正在升级 pip / setuptools / wheel…", flush=True)
    ret = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if ret.returncode != 0:
        print("⚠️ pip 自升级失败，将继续尝试安装 BFF 依赖", flush=True)


def _node_toolchain_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


def check_runtime_prerequisites() -> Tuple[bool, str]:
    py_min = python_minimum()
    if sys.version_info < py_min:
        return False, (
            f"Python 版本过低，当前 {sys.version_info.major}.{sys.version_info.minor}，"
            f"需要 >= {py_min[0]}.{py_min[1]}"
        )
    if not BFF_REQUIREMENTS.is_file():
        return False, f"缺少 BFF 依赖文件: {BFF_REQUIREMENTS}"

    if ui_dev_mode():
        if not _node_toolchain_available():
            return False, "开发模式（launcher.py -d）需要 Node.js 与 npm"
        if not (FED_ROOT / "package.json").is_file():
            return False, f"缺少 FED package.json: {FED_ROOT / 'package.json'}"
        return True, "ok"

    if fed_build_ready():
        return True, "ok"

    if _node_toolchain_available():
        return True, "ok"

    return (
        False,
        "未找到 core/ui/fed/build/。请 npm run build，或使用 launcher.py -d",
    )


def _pip_install_bff() -> None:
    pip_cmd = [sys.executable, "-m", "pip", "install", "--no-compile", "--prefer-binary"]
    if _env_truthy("NTQ_PIP_NO_CACHE"):
        pip_cmd.append("--no-cache-dir")
    pip_cmd.extend(["-r", str(BFF_REQUIREMENTS)])
    if subprocess.run(pip_cmd, cwd=str(REPO_ROOT)).returncode != 0:
        raise RuntimeError("安装 BFF Python 依赖失败")


def _npm_install_fed() -> None:
    if subprocess.run(["npm", "install"], cwd=str(FED_ROOT)).returncode != 0:
        raise RuntimeError("安装 FED Node 依赖失败")


def _npm_build_fed() -> None:
    print("正在构建 FED（npm run build）…", flush=True)
    if subprocess.run(["npm", "run", "build"], cwd=str(FED_ROOT)).returncode != 0:
        raise RuntimeError("FED 构建失败")
    if not fed_build_ready():
        raise RuntimeError(f"构建完成但未找到 {UI_FED_BUILD_DIR / 'index.html'}")


def install_ui_runtime(force: bool = False) -> None:
    if not force and not needs_install("ui"):
        print("安装检查通过，跳过依赖安装。", flush=True)
        return

    _bootstrap_pip()
    _pip_install_bff()

    fingerprints: dict = {
        "python": {
            "uiRequirementsHash": sha256_file(BFF_REQUIREMENTS),
            "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }

    if ui_dev_mode():
        print("安装 UI 开发依赖（BFF + node_modules）…", flush=True)
        _npm_install_fed()
        fingerprints["node"] = {
            "fedLockHash": sha256_file(FED_LOCKFILE),
            "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    else:
        print("安装 UI 运行依赖（BFF + fed/build）…", flush=True)
        if not fed_build_ready():
            if not _node_toolchain_available():
                raise RuntimeError("缺少 fed/build 且未检测到 Node.js")
            _npm_install_fed()
            _npm_build_fed()
        fingerprints["fedBuild"] = {
            "buildFingerprint": fed_build_fingerprint(),
            "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    mark_runtime("ui", success=True, fingerprints=fingerprints)
    print("UI 运行依赖安装完成。", flush=True)


def _pids_listening_on(port: int) -> list[int]:
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    return [int(line) for line in out.stdout.splitlines() if line.strip().isdigit()]


def _process_cmdline(pid: int) -> str:
    try:
        out = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    return (out.stdout or "").strip()


def _release_stale_listen_port(port: int, *, match_substrings: tuple[str, ...]) -> None:
    fed_root = str(FED_ROOT.resolve())

    def _should_kill(cmd: str) -> bool:
        return bool(cmd) and (any(s in cmd for s in match_substrings) or fed_root in cmd)

    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in _pids_listening_on(port):
            if _should_kill(_process_cmdline(pid)):
                print(f"结束占用 {port} 的旧进程 pid={pid}", flush=True)
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass
        if not _pids_listening_on(port):
            return
        if sig == signal.SIGTERM:
            time.sleep(1)


def _wait_http_ok(url: str, timeout_sec: int = 30) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 400:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(1)
    return False


def _ui_url(*, dev: bool, bff_host: str, bff_port: int) -> str:
    if dev:
        return f"http://localhost:{FED_DEV_PORT}/strategy-workbench"
    return f"http://{bff_host}:{bff_port}/strategy-workbench"


def _fed_dev_env() -> dict[str, str]:
    env = os.environ.copy()
    env["BROWSER"] = "none"
    env["PORT"] = str(FED_DEV_PORT)
    env["DANGEROUSLY_DISABLE_HOST_CHECK"] = "true"
    return env


def launch_ui_stack() -> None:
    bff_host = os.getenv("NTQ_BFF_HOST", "127.0.0.1")
    bff_port = int(os.getenv("NTQ_BFF_PORT", str(BFF_DEFAULT_PORT)))
    dev = ui_dev_mode()
    ui_url = _ui_url(dev=dev, bff_host=bff_host, bff_port=bff_port)

    _release_stale_listen_port(bff_port, match_substrings=("core.ui.bff.app",))

    bff_env = os.environ.copy()
    bff_env["NTQ_BFF_HOST"] = bff_host
    bff_env["NTQ_BFF_PORT"] = str(bff_port)
    bff_proc = subprocess.Popen(
        [sys.executable, "-m", "core.ui.bff.app"],
        cwd=str(REPO_ROOT),
        env=bff_env,
    )

    if not _wait_http_ok(f"http://{bff_host}:{bff_port}/api/health"):
        bff_proc.terminate()
        raise RuntimeError("BFF 启动超时（/api/health）")

    fed_proc = None
    if dev:
        _release_stale_listen_port(
            FED_DEV_PORT,
            match_substrings=("react-scripts", "webpack"),
        )
        fed_proc = subprocess.Popen(
            ["npm", "start"],
            cwd=str(FED_ROOT),
            env=_fed_dev_env(),
        )
        print(f"开发模式：BFF :{bff_port} + FED :{FED_DEV_PORT}", flush=True)
        if not _wait_http_ok(ui_url, timeout_sec=180):
            print(f"⚠️ FED 未就绪，请查看 npm 输出；目标地址: {ui_url}", flush=True)
    else:
        if not fed_build_ready():
            bff_proc.terminate()
            raise RuntimeError("缺少 fed/build，请 npm run build")
        print(f"生产模式：BFF :{bff_port} 托管静态资源", flush=True)
        if not _wait_http_ok(ui_url, timeout_sec=30):
            bff_proc.terminate()
            raise RuntimeError(f"前端未就绪: {ui_url}")

    if _wait_http_ok(ui_url, timeout_sec=3):
        print(f"访问: {ui_url}", flush=True)
        try:
            webbrowser.open(ui_url)
        except Exception:
            pass
    else:
        print(f"请手动打开: {ui_url}", flush=True)

    try:
        (fed_proc or bff_proc).wait()
    except KeyboardInterrupt:
        print("\n正在关闭…", flush=True)
    finally:
        for proc in (fed_proc, bff_proc):
            if proc is not None and proc.poll() is None:
                proc.terminate()
        for proc in (fed_proc, bff_proc):
            if proc is None:
                continue
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
