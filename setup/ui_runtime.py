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

    ui_url = f"http://{host}:{port}/strategy-workbench"
    fed_proc = None

    if ui_dev_mode():
        fed_env = os.environ.copy()
        fed_cmd = ["npm", "start"]
        fed_proc = subprocess.Popen(fed_cmd, cwd=str(FED_ROOT), env=fed_env)
        ui_url = "http://localhost:8888/strategy-workbench"
        print("UI 已启动：BFF + FED 开发服务器", flush=True)
        print("FED 开发地址: http://localhost:8888/strategy-workbench", flush=True)
    else:
        if not fed_build_ready():
            bff_proc.terminate()
            raise RuntimeError(
                "FED 静态资源未就绪。请运行：cd core/ui/fed && npm run build"
            )
        print("UI 已启动：BFF（托管 FED 构建产物）", flush=True)
        print(f"访问地址: {ui_url}", flush=True)

    try:
        webbrowser.open(ui_url)
    except Exception:
        pass

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
