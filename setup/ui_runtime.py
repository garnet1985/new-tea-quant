from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from typing import Tuple

from core.system import python_minimum
from core.ui.process_cleanup import kill_process_group
from core.ui.ports import ALL_UI_PORTS, UI_BFF_PORT, UI_DEV_PORT
from core.infra.cmd_layout import IconService

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
        print(f"{IconService.get('warning')} pip 自升级失败，将继续尝试安装 BFF 依赖", flush=True)


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
    pip_cmd = [sys.executable, "-m", "pip", "install", "--no-compile", "--only-binary", "numpy,pandas,duckdb,psycopg2-binary,cffi,curl-cffi,lxml,mini-racer,psutil"]
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


def _wait_port_free(port: int, *, timeout_sec: float = 15.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not _pids_listening_on(port):
            return True
        time.sleep(0.25)
    return not _pids_listening_on(port)


def _release_stale_listen_port(port: int, *, match_substrings: tuple[str, ...]) -> None:
    fed_root = str(FED_ROOT.resolve())

    def _should_kill(cmd: str) -> bool:
        return bool(cmd) and (any(s in cmd for s in match_substrings) or fed_root in cmd)

    for attempt in range(2):
        for pid in _pids_listening_on(port):
            cmd = _process_cmdline(pid)
            if _should_kill(cmd):
                print(f"结束占用 {port} 的旧进程 pid={pid}", flush=True)
                try:
                    kill_process_group(pid, grace_sec=2.0 if attempt == 0 else 0.5)
                except ProcessLookupError:
                    pass
        if _wait_port_free(port, timeout_sec=8.0):
            return


def _force_shutdown_ui_ports() -> None:
    """退出时强制释放 UI 端口（不依赖 cmdline，避免 CRA node 孤儿）。"""
    for port in ALL_UI_PORTS:
        for attempt in range(2):
            pids = _pids_listening_on(port)
            if not pids:
                break
            for pid in pids:
                cmd = _process_cmdline(pid)
                label = cmd[:80] if cmd else "(unknown)"
                print(f"结束 UI 进程 pid={pid}（:{port}） {label}", flush=True)
                try:
                    kill_process_group(pid, grace_sec=2.0 if attempt == 0 else 0.5)
                except ProcessLookupError:
                    pass
            if _wait_port_free(port, timeout_sec=8.0):
                break
    blocked = [p for p in ALL_UI_PORTS if _pids_listening_on(p)]
    if blocked:
        print(f"{IconService.get('warning')} 端口仍占用: {blocked}，请执行 python devcli.py uk", flush=True)


def release_ui_listen_ports(ports: tuple[int, ...] = ALL_UI_PORTS) -> None:
    """启动前清掉指定 UI 端口上的 NTQ 监听进程。"""
    markers = (
        "core.ui.bff.app",
        "react-scripts",
        "webpack",
        "webpack-dev-server",
        "launcher.py",
        "devcli.py",
        str(FED_ROOT.resolve()),
        str(REPO_ROOT),
    )
    for port in ports:
        _release_stale_listen_port(port, match_substrings=markers)
    blocked = [p for p in ports if _pids_listening_on(p)]
    if blocked:
        print(f"{IconService.get('warning')} 端口仍被占用: {blocked}，后续启动可能失败", flush=True)


def _wait_http_ok(url: str, timeout_sec: int = 30) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if 200 <= resp.status < 400:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            pass
        time.sleep(0.5)
    return False


def _warm_bff_api(host: str, port: int) -> None:
    """预加载 strategy 栈，避免 CRA 首屏并发请求时 BFF 冷启动导致 proxy ECONNRESET。"""
    url = f"http://{host}:{port}/api/v1/strategies/list?page=1&limit=1"
    print("正在预加载 BFF API（首次较慢）…", flush=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            resp.read()
        print("BFF API 预加载完成", flush=True)
    except Exception as exc:
        print(f"{IconService.get('warning')} BFF API 预加载失败: {exc}", flush=True)


def _fed_dev_env() -> dict[str, str]:
    env = os.environ.copy()
    env["BROWSER"] = "none"
    env["PORT"] = str(UI_DEV_PORT)
    env["DANGEROUSLY_DISABLE_HOST_CHECK"] = "true"
    return env


def _terminate_proc(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    kill_process_group(proc.pid, grace_sec=3.0)
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        kill_process_group(proc.pid, grace_sec=0.5)
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _shutdown_ui_stack_procs(
    *,
    bff_proc: subprocess.Popen | None,
    fed_proc: subprocess.Popen | None,
) -> None:
    """结束 CRA/BFF 子进程；若进程组信号未生效，按端口兜底（避免 Ctrl+C 后孤儿 BFF）。"""
    _terminate_proc(bff_proc)
    _terminate_proc(fed_proc)
    _force_shutdown_ui_ports()


def launch_ui_stack() -> None:
    host = os.getenv("NTQ_BFF_HOST", "127.0.0.1").strip() or "127.0.0.1"
    dev = ui_dev_mode()

    release_ui_listen_ports(ALL_UI_PORTS)

    bff_env = os.environ.copy()
    bff_env["NTQ_BFF_HOST"] = host
    bff_env["NTQ_BFF_PORT"] = str(UI_BFF_PORT)
    bff_env.pop("NTQ_UI_DEV_GATEWAY", None)
    bff_env.pop("NTQ_WEBPACK_DEV_UPSTREAM", None)
    if dev:
        bff_env["NTQ_UI_DEV"] = "1"
    else:
        bff_env.pop("NTQ_UI_DEV", None)

    bff_proc: subprocess.Popen | None = None
    fed_proc: subprocess.Popen | None = None
    try:
        bff_proc = subprocess.Popen(
            [sys.executable, "-m", "core.ui.bff.app"],
            cwd=str(REPO_ROOT),
            env=bff_env,
        )

        health_url = f"http://{host}:{UI_BFF_PORT}/api/health"
        if not _wait_http_ok(health_url, timeout_sec=90):
            raise RuntimeError(f"BFF 启动超时（{health_url}）")

        _warm_bff_api(host, UI_BFF_PORT)

        if dev:
            fed_proc = subprocess.Popen(
                ["npm", "start"],
                cwd=str(FED_ROOT),
                env=_fed_dev_env(),
            )
            ui_url = f"http://localhost:{UI_DEV_PORT}/strategy-design"
            print(
                f"开发模式：浏览器 http://localhost:{UI_DEV_PORT} "
                f"（共享 BFF :{UI_BFF_PORT} 仅 /api，不挂载 fed/build）",
                flush=True,
            )
            if not _wait_http_ok(f"http://localhost:{UI_DEV_PORT}/", timeout_sec=180):
                print(f"{IconService.get('warning')} CRA 未就绪，请查看 npm 输出；目标: {ui_url}", flush=True)
            elif not _wait_http_ok(f"http://{host}:{UI_BFF_PORT}/api/health", timeout_sec=15):
                print(f"{IconService.get('warning')} BFF 在 CRA 就绪后未响应，/api 代理可能失败", flush=True)
        else:
            if not fed_build_ready():
                raise RuntimeError("缺少 fed/build，请 npm run build 或使用 launcher.py -d")
            ui_url = f"http://{host}:{UI_BFF_PORT}/strategy-design"
            print(f"生产模式：入口 {ui_url}", flush=True)
            if not _wait_http_ok(ui_url, timeout_sec=30):
                raise RuntimeError(f"前端未就绪: {ui_url}")

        if _wait_http_ok(ui_url, timeout_sec=5):
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
    except KeyboardInterrupt:
        print("\n正在关闭…", flush=True)
    finally:
        _shutdown_ui_stack_procs(bff_proc=bff_proc, fed_proc=fed_proc)
