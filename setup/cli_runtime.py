"""
CLI 应用安装编排（setup 步骤流水线）。

判断逻辑见 ``setup.install_runtime.needs_install("cli")``。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

from setup.install_runtime import (
    REPO_ROOT,
    REQUIREMENTS,
    mark_runtime,
    needs_install,
    sha256_file,
)
from setup.meta_loader import load_setup_step_meta
from setup.setup import NewTeaQuantSetup

CLI_INSTALL_STEPS: Tuple[str, ...] = (
    "sys_req_check",
    "resolve_deps",
    "init_userspace",
    "db_connection",
    "import_data",
)


def _ordered_cli_steps() -> List[str]:
    metas = load_setup_step_meta(ui_only=True)
    if metas:
        return [str(s["id"]) for s in metas]
    return list(CLI_INSTALL_STEPS)


def _run_step(step_id: str) -> int:
    env_backup = os.environ.get("NTQ_USERSPACE_CONFLICT_POLICY")
    if step_id == "init_userspace":
        os.environ["NTQ_USERSPACE_CONFLICT_POLICY"] = (
            os.environ.get("NTQ_USERSPACE_CONFLICT_POLICY", "skip").strip().lower() or "skip"
        )
    try:
        return NewTeaQuantSetup.run_install_script(step_id)
    finally:
        if step_id == "init_userspace":
            if env_backup is None:
                os.environ.pop("NTQ_USERSPACE_CONFLICT_POLICY", None)
            else:
                os.environ["NTQ_USERSPACE_CONFLICT_POLICY"] = env_backup


def install_cli_runtime(force: bool = False) -> None:
    if not force and not needs_install("cli"):
        print("CLI 安装检查通过，跳过安装步骤。", flush=True)
        return

    NewTeaQuantSetup.to_root_dir()
    steps = _ordered_cli_steps()
    print(f"开始 CLI 应用安装（共 {len(steps)} 步）…", flush=True)

    for i, step_id in enumerate(steps, start=1):
        NewTeaQuantSetup.print_check_item("running", f"[{i}/{len(steps)}] {step_id}")
        code = _run_step(step_id)
        if code != 0:
            mark_runtime("cli", success=False, failed_step_id=step_id)
            raise RuntimeError(f"安装步骤失败: {step_id} (exit={code})")
        NewTeaQuantSetup.print_check_item("done", f"[{i}/{len(steps)}] {step_id}")

    mark_runtime(
        "cli",
        success=True,
        fingerprints={
            "cli": {
                "requirementsHash": sha256_file(REQUIREMENTS),
                "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        },
    )
    print("CLI 应用安装完成。", flush=True)


def ensure_cli_install_via_install_py() -> int:
    """通过根目录 ``install.py`` 执行 CLI 安装（``start-cli`` 自动触发时使用）。"""
    script = REPO_ROOT / "install.py"
    if not script.is_file():
        print(f"❌ 未找到安装入口: {script}", flush=True)
        return 1
    proc = subprocess.run([sys.executable, str(script)], cwd=str(REPO_ROOT))
    return int(proc.returncode)
