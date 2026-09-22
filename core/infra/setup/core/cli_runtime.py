"""CLI 安装编排：冷启动 ``install.py`` 与 ``cli.py --if-needed``。"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from core.infra.cmd_layout import CmdLayout
from core.infra.setup.core.cli_install_options import (
    CliInstallOptions,
    db_inputs_from_options,
    userspace_inputs_from_options,
    validate_cli_install_options,
)
from core.infra.setup.core.db_install_config import write_database_install_config
from core.infra.setup.core.env import NewTeaQuantSetup
from core.infra.setup.core.install_runtime import (
    REPO_ROOT,
    mark_cli_success_fingerprint,
    mark_runtime,
    needs_install,
)
from core.infra.setup.core.meta_loader import load_setup_step_meta
from core.infra.setup.core import setup_session
from core.infra.setup.core.trace_events import SetupTrace

INSTALL_PY = REPO_ROOT / "install.py"


def _ordered_cli_steps() -> List[str]:
    metas = load_setup_step_meta(ui_only=False)
    if metas:
        return [str(s["id"]) for s in metas if not bool(s.get("cliSkip"))]
    return [
        "sys_req_check",
        "resolve_deps",
        "init_userspace",
        "db_connection",
        "import_data",
    ]


def _run_step(step_id: str, options: Optional[CliInstallOptions] = None) -> int:
    options = options or CliInstallOptions()
    extra_env: dict[str, str] = {}
    if step_id == "init_userspace":
        target = str(options.userspace or "").strip()
        if target:
            extra_env["NTQ_USERSPACE_TARGET_PATH"] = str(Path(target).expanduser().resolve())
        extra_env["NTQ_USERSPACE_CONFLICT_POLICY"] = options.conflict_policy
    return NewTeaQuantSetup.run_install_script(step_id, extra_env=extra_env or None)


def _default_userspace_path() -> str:
    from core.infra.project_context import ProjectContext

    return str(ProjectContext.path.resolve_userspace_target(None))


def _userspace_root_after_init(options: CliInstallOptions) -> Path:
    from core.infra.project_context import ProjectContext

    ProjectContext.cache.clear_userspace_cache()
    target = str(options.userspace or "").strip()
    if target:
        return Path(target).expanduser().resolve()
    return Path(ProjectContext.path.get_userspace_root()).resolve()


def _session_inputs(options: CliInstallOptions) -> dict:
    inputs = {
        "init_userspace": userspace_inputs_from_options(
            options, _default_userspace_path()
        ),
    }
    db_inputs = db_inputs_from_options(options)
    if db_inputs is None:
        db_inputs = {"dbType": "duckdb"}
    inputs["db_connection"] = db_inputs
    return inputs


def _apply_db_config(options: CliInstallOptions) -> None:
    db_inputs = db_inputs_from_options(options)
    if db_inputs is None:
        return
    userspace_root = _userspace_root_after_init(options)
    write_database_install_config(userspace_root, db_inputs)


def install_cli_runtime(
    force: bool = False,
    options: Optional[CliInstallOptions] = None,
) -> None:
    options = options or CliInstallOptions()
    validate_cli_install_options(options)

    if not force and not needs_install("cli"):
        print("CLI 安装状态已就绪。", flush=True)
        return

    NewTeaQuantSetup.to_root_dir()
    SetupTrace.ensure_install_id()
    started = time.monotonic()
    step_seconds: dict = {}
    session_inputs = _session_inputs(options)
    current_step_id = ""

    print()
    print("=" * 60)
    print("  New Tea Quant — 安装")
    print("=" * 60)
    print()

    try:
        for step_id in _ordered_cli_steps():
            current_step_id = step_id
            NewTeaQuantSetup.print_check_item("running", f"步骤: {step_id}")
            setup_session.record_step(
                step_id,
                setup_session.STATUS_RUNNING,
                inputs=session_inputs.get(step_id),
                source="cli",
            )
            t0 = time.monotonic()
            if step_id == "db_connection":
                _apply_db_config(options)
            code = _run_step(step_id, options)
            step_seconds[step_id] = round(max(0.0, time.monotonic() - t0), 2)
            if code != 0:
                raise RuntimeError(f"步骤失败: {step_id}（exit={code}），详见上方日志")
            setup_session.record_step(
                step_id,
                setup_session.STATUS_SUCCESS,
                inputs=session_inputs.get(step_id),
                source="cli",
            )
    except Exception as exc:
        failed_step = current_step_id
        message = str(exc)
        if failed_step:
            setup_session.mark_pipeline_failed(failed_step, message, source="cli")
        mark_runtime("cli", success=False, failed_step_id=failed_step)
        SetupTrace.install_step_failed(
            step=failed_step or "cli_install",
            entry="cli",
            message=message,
            exc=exc,
        )
        SetupTrace.install_complete(
            success=False,
            entry="cli",
            error_code=failed_step or "cli_install",
            elapsed_seconds=time.monotonic() - started,
            step_seconds=step_seconds,
        )
        print(f"{CmdLayout.icon.get('error')} 安装失败: {exc}", flush=True)
        raise

    setup_session.mark_pipeline_complete(source="cli", inputs_by_step=session_inputs)
    mark_cli_success_fingerprint()

    print()
    NewTeaQuantSetup.print_check_ok("安装完成")
    print()
    print("下一步:")
    print("  python cli.py --help")
    print("=" * 60)
    SetupTrace.install_complete(
        success=True,
        entry="cli",
        elapsed_seconds=time.monotonic() - started,
        step_seconds=step_seconds,
    )


def ensure_cli_install_via_install_py() -> int:
    """
    通过根目录 ``install.py --if-needed`` 执行 CLI 安装（user CLI 自动触发）。

    冷启动与显式 ``python install.py`` 共用同一入口。
    """
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(
        [sys.executable, str(INSTALL_PY), "--if-needed"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    return int(proc.returncode)
