"""安装编排入口：CLI / UI / session 集中调度。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.infra.setup.core.orchestrator import session
from core.infra.setup.core.orchestrator.cli import (
    ensure_cli_install_via_install_py,
    install_cli_runtime,
)
from core.infra.setup.core.orchestrator.options import CliInstallOptions
from core.infra.setup.core.orchestrator.ui import (
    check_runtime_prerequisites,
    install_ui_runtime,
    launch_ui_stack,
)


class InstallOrchestrator:
    """静态方法类：CLI / UI 安装与会话状态调度。"""

    # —— session（``.ntq/setup-runtime.json``）——
    STATUS_NOT_STARTED = session.STATUS_NOT_STARTED
    STATUS_WAITING_INPUT = session.STATUS_WAITING_INPUT
    STATUS_RUNNING = session.STATUS_RUNNING
    STATUS_SUCCESS = session.STATUS_SUCCESS
    STATUS_FAILED = session.STATUS_FAILED
    STATE_FILE = session.STATE_FILE

    @staticmethod
    def is_ready() -> bool:
        return session.is_ready()

    @staticmethod
    def new_state(definition: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return session.new_state(definition)

    @staticmethod
    def load_state(definition: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return session.load_state(definition)

    @staticmethod
    def save_state(state: Dict[str, Any]) -> None:
        session.save_state(state)

    @staticmethod
    def record_step(
        step_id: str,
        status: str,
        *,
        error: str = "",
        inputs: Optional[Dict[str, Any]] = None,
        source: str = "cli",
    ) -> Dict[str, Any]:
        return session.record_step(
            step_id, status, error=error, inputs=inputs, source=source
        )

    @staticmethod
    def mark_pipeline_complete(
        *,
        source: str,
        inputs_by_step: Optional[Dict[str, Any]] = None,
        skipped_step_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return session.mark_pipeline_complete(
            source=source,
            inputs_by_step=inputs_by_step,
            skipped_step_ids=skipped_step_ids,
        )

    @staticmethod
    def mark_pipeline_failed(
        step_id: str,
        error: str,
        *,
        source: str = "cli",
    ) -> Dict[str, Any]:
        return session.mark_pipeline_failed(step_id, error, source=source)

    @staticmethod
    def set_step_status(
        state: Dict[str, Any],
        step_id: str,
        status: str,
        error_message: str = "",
    ) -> None:
        session.set_step_status(state, step_id, status, error_message)

    @staticmethod
    def record_inputs(
        state: Dict[str, Any], step_id: str, inputs: Dict[str, Any]
    ) -> None:
        session.record_inputs(state, step_id, inputs)

    @staticmethod
    def refresh_ready(
        state: Dict[str, Any],
        definition: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        session.refresh_ready(state, definition)

    # —— CLI ——
    @staticmethod
    def install_cli(
        force: bool = False,
        options: Optional[CliInstallOptions] = None,
    ) -> None:
        install_cli_runtime(force=force, options=options)

    @staticmethod
    def ensure_cli_install_via_install_py() -> int:
        return ensure_cli_install_via_install_py()

    # —— UI ——
    @staticmethod
    def install_ui(force: bool = False) -> None:
        install_ui_runtime(force=force)

    @staticmethod
    def check_runtime_prerequisites() -> Tuple[bool, str]:
        return check_runtime_prerequisites()

    @staticmethod
    def launch_ui_stack() -> None:
        launch_ui_stack()
