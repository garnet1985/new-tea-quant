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

UI_ROOT = REPO_ROOT / "core" / "ui"
BFF_ROOT = UI_ROOT / "bff"
FED_ROOT = UI_FED_ROOT
BFF_REQUIREMENTS = UI_BFF_REQUIREMENTS
FED_LOCKFILE = UI_FED_LOCKFILE
FED_NODE_MODULES = REPO_ROOT / "core" / "ui" / "fed" / "node_modules"
# Chrome 会拦截 6665–6669（ERR_UNSAFE_PORT），勿用 6666
FED_DEV_PORT = 8000
BFF_DEFAULT_PORT = 8888


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _bootstrap_pip() -> None:
    """Upgrade pip/setuptools/wheel so dependency resolution matches modern Flask stacks."""
    if _env_truthy("NTQ_SKIP_PIP_BOOTSTRAP"):
        return
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if _env_truthy("NTQ_PIP_NO_CACHE"):
        cmd.append("--no-cache-dir")
    cmd.extend(["pip>=24.0", "setuptools>=65", "wheel"])
    print("正在升级 pip / setuptools / wheel（缓解依赖解析冲突）...", flush=True)
    ret = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if ret.returncode != 0:
        print("⚠️ pip 自升级失败，将继续尝试安装 BFF 依赖；若仍失败请手动: python -m pip install -U pip", flush=True)


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
            return False, "开发模式（launcher.py -d / -dev）需要 Node.js 与 npm"
        if not (FED_ROOT / "package.json").is_file():
            return False, f"缺少 FED package.json: {FED_ROOT / 'package.json'}"
        return True, "ok"

    if fed_build_ready():
        return True, "ok"

    if _node_toolchain_available():
        return True, "ok"

    return (
        False,
        "未找到 FED 构建产物（core/ui/fed/build/）。请安装 Node.js 后执行 "
        "cd core/ui/fed && npm install && npm run build，或使用 launcher.py -d 开发模式。",
    )


def _pip_install_bff() -> None:
    pip_cmd = [sys.executable, "-m", "pip", "install", "--no-compile", "--prefer-binary"]
    if _env_truthy("NTQ_PIP_NO_CACHE"):
        pip_cmd.append("--no-cache-dir")
    pip_cmd.extend(["-r", str(BFF_REQUIREMENTS)])
    pip_ret = subprocess.run(pip_cmd, cwd=str(REPO_ROOT))
    if pip_ret.returncode != 0:
        raise RuntimeError("安装 BFF Python 依赖失败")


def _npm_install_fed() -> None:
    npm_ret = subprocess.run(["npm", "install"], cwd=str(FED_ROOT))
    if npm_ret.returncode != 0:
        raise RuntimeError("安装 FED Node 依赖失败")


def _npm_build_fed() -> None:
    print("正在构建 FED 静态资源（npm run build）…", flush=True)
    build_ret = subprocess.run(["npm", "run", "build"], cwd=str(FED_ROOT))
    if build_ret.returncode != 0:
        raise RuntimeError("FED 构建失败（npm run build）")
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
        print("开始安装 UI 开发依赖（BFF + FED node_modules）...", flush=True)
        _npm_install_fed()
        fingerprints["node"] = {
            "fedLockHash": sha256_file(FED_LOCKFILE),
            "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    else:
        print("开始安装 UI 运行依赖（BFF + FED 静态构建）...", flush=True)
        if not fed_build_ready():
            if not _node_toolchain_available():
                raise RuntimeError(
                    "缺少 core/ui/fed/build/ 且未检测到 Node.js。"
                    "请先执行：cd core/ui/fed && npm install && npm run build"
                )
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
    pids: list[int] = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


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
    """结束占用端口的本仓库旧 UI 进程，避免 CRA 交互式换端口或 BFF 启动失败。"""
    fed_root = str(FED_ROOT.resolve())
    for pid in _pids_listening_on(port):
        cmd = _process_cmdline(pid)
        if not cmd:
            continue
        if not any(s in cmd for s in match_substrings) and fed_root not in cmd:
            continue
        print(f"正在结束占用端口 {port} 的旧进程 (pid {pid})…", flush=True)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
    if _pids_listening_on(port):
        time.sleep(1)
        for pid in _pids_listening_on(port):
            cmd = _process_cmdline(pid)
            if not cmd:
                continue
            if not any(s in cmd for s in match_substrings) and fed_root not in cmd:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


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


def _wait_bff_ready(host: str, port: int, timeout_sec: int = 30) -> bool:
    return _wait_http_ok(f"http://{host}:{port}/api/health", timeout_sec)


def _public_ui_url(host: str, port: int, *, dev: bool) -> str:
    if dev:
        return f"http://localhost:{FED_DEV_PORT}/strategy-workbench"
    return f"http://{host}:{port}/strategy-workbench"


def launch_ui_stack() -> None:
    host = os.getenv("NTQ_BFF_HOST", "127.0.0.1")
    port = int(os.getenv("NTQ_BFF_PORT", str(BFF_DEFAULT_PORT)))

    _release_stale_listen_port(port, match_substrings=("core.ui.bff.app",))

    bff_env = os.environ.copy()
    bff_env["NTQ_BFF_HOST"] = host
    bff_env["NTQ_BFF_PORT"] = str(port)
    bff_cmd = [sys.executable, "-m", "core.ui.bff.app"]
    bff_proc = subprocess.Popen(bff_cmd, cwd=str(REPO_ROOT), env=bff_env)

    if not _wait_bff_ready(host, port):
        bff_proc.terminate()
        raise RuntimeError("BFF 启动超时，未通过健康检查 /api/health")

    dev = ui_dev_mode()
    ui_url = _public_ui_url(host, port, dev=dev)
    fed_proc = None

    if dev:
        _release_stale_listen_port(
            FED_DEV_PORT,
            match_substrings=("react-scripts", "webpack", "node"),
        )
        fed_env = os.environ.copy()
        fed_env.setdefault("BROWSER", "none")
        fed_env.setdefault("PORT", str(FED_DEV_PORT))
        fed_env.setdefault("DANGEROUSLY_DISABLE_HOST_CHECK", "true")
        fed_cmd = ["npm", "start"]
        fed_proc = subprocess.Popen(fed_cmd, cwd=str(FED_ROOT), env=fed_env)
        print("UI 已启动：BFF + FED 开发服务器", flush=True)
        print(f"等待 FED 编译就绪（端口 {FED_DEV_PORT}，首次约 1–2 分钟）…", flush=True)
        if not _wait_http_ok(ui_url, timeout_sec=180):
            print(
                f"⚠️ FED 开发服务未在 {FED_DEV_PORT} 端口就绪。"
                f"请查看终端 npm 是否出现 Compiled successfully；就绪后访问: {ui_url}",
                flush=True,
            )
        else:
            print(f"FED 开发地址: {ui_url}", flush=True)
            print(
                "请在 Chrome/Safari 打开上述地址；勿用 Cursor 内置预览，"
                "勿用 127.0.0.1（与 localhost 等效即可）；Chrome 禁止访问 6666 等端口。",
                flush=True,
            )
    else:
        if not fed_build_ready():
            bff_proc.terminate()
            raise RuntimeError(
                "FED 静态资源未就绪。请运行：cd core/ui/fed && npm run build"
            )
        print("UI 已启动：BFF（托管 FED 构建产物）", flush=True)
        if not _wait_http_ok(ui_url, timeout_sec=30):
            bff_proc.terminate()
            raise RuntimeError(
                f"前端页面未就绪: {ui_url}。"
                "请确认 core/ui/fed/build 已提交且 BFF 静态路由正常。"
            )
        print(f"访问地址: {ui_url}", flush=True)
        print(
            f"（生产模式端口 {port}；开发模式 FED 端口 {FED_DEV_PORT}，请使用 launcher.py -d）",
            flush=True,
        )

    if _wait_http_ok(ui_url, timeout_sec=3):
        try:
            webbrowser.open(ui_url)
        except Exception:
            pass
    else:
        print(f"请手动在浏览器打开: {ui_url}", flush=True)

    try:
        if fed_proc is not None:
            fed_proc.wait()
        else:
            bff_proc.wait()
    except KeyboardInterrupt:
        print("\n收到中断，正在关闭服务...", flush=True)
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
