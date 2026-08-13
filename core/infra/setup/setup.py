"""Setup 门面 — env / runtime / artifacts / meta / trace / types。

方法内懒导入，避免 ``from core.infra.setup import Setup`` 拉起 UI 启动链。
CLI / install.py / launcher.py / BFF 只应依赖本门面，不深挖 steps/scripts。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.infra.setup.contracts import (
    AppEntry,
    CliInstallScope,
    InstallEntry,
    InstallProfileName,
)


class TypesNamespace:
    InstallProfileName = InstallProfileName
    CliInstallScope = CliInstallScope
    InstallEntry = InstallEntry
    AppEntry = AppEntry


class EnvNamespace:
    """仓库路径、venv、工作目录（安装引导）。"""

    @staticmethod
    def repo_root() -> Path:
        from core.infra.setup.core.env import NewTeaQuantSetup

        return NewTeaQuantSetup.repo_root

    @staticmethod
    def venv_python() -> Path:
        from core.infra.setup.core.env import NewTeaQuantSetup

        return NewTeaQuantSetup.venv_python()

    @staticmethod
    def in_virtualenv() -> bool:
        from core.infra.setup.core.env import NewTeaQuantSetup

        return NewTeaQuantSetup.in_virtualenv()

    @staticmethod
    def ensure_sys_path() -> None:
        from core.infra.setup.core.env import NewTeaQuantSetup

        NewTeaQuantSetup.ensure_sys_path()

    @staticmethod
    def to_root_dir() -> None:
        from core.infra.setup.core.env import NewTeaQuantSetup

        NewTeaQuantSetup.to_root_dir()

    @staticmethod
    def ensure_venv(entry_script: str | Path | None = None) -> None:
        from core.infra.setup.core.env import NewTeaQuantSetup

        NewTeaQuantSetup.ensure_venv(entry_script=entry_script)

    @staticmethod
    def ensure_venv_for_setup_step(script_path: str | Path) -> None:
        from core.infra.setup.core.env import NewTeaQuantSetup

        NewTeaQuantSetup.ensure_venv_for_setup_step(script_path)

    @staticmethod
    def requirements_txt() -> Path:
        from core.infra.setup.core.install_runtime import REQUIREMENTS

        return REQUIREMENTS

    @staticmethod
    def ui_bff_requirements() -> Path:
        from core.infra.setup.core.install_runtime import UI_BFF_REQUIREMENTS

        return UI_BFF_REQUIREMENTS

    @staticmethod
    def ui_fed_root() -> Path:
        from core.infra.setup.core.install_runtime import UI_FED_ROOT

        return UI_FED_ROOT


class RuntimeNamespace:
    """安装状态判断与 CLI/UI 安装编排。"""

    @staticmethod
    def needs_install(profile: InstallProfileName) -> bool:
        from core.infra.setup.core.install_runtime import needs_install

        return needs_install(profile)

    @staticmethod
    def cli_install_scope() -> CliInstallScope:
        from core.infra.setup.core.install_runtime import cli_install_scope

        return cli_install_scope()

    @staticmethod
    def install_cli(*, force: bool = False) -> None:
        from core.infra.setup.core.cli_runtime import install_cli_runtime

        install_cli_runtime(force=force)

    @staticmethod
    def ensure_cli_install() -> int:
        """通过根目录 ``install.py`` 执行 CLI 安装（user CLI 自动触发）。"""
        from core.infra.setup.core.cli_runtime import ensure_cli_install_via_install_py

        return ensure_cli_install_via_install_py()

    @staticmethod
    def install_ui(*, force: bool = False) -> None:
        from core.infra.setup.core.ui_runtime import install_ui_runtime

        install_ui_runtime(force=force)

    @staticmethod
    def check_ui_prerequisites() -> tuple[bool, str]:
        from core.infra.setup.core.ui_runtime import check_runtime_prerequisites

        return check_runtime_prerequisites()

    @staticmethod
    def launch_ui() -> None:
        from core.infra.setup.core.ui_runtime import launch_ui_stack

        launch_ui_stack()

    @staticmethod
    def set_ui_dev_mode(enabled: bool) -> None:
        from core.infra.setup.core.install_runtime import set_ui_dev_mode

        set_ui_dev_mode(enabled)

    @staticmethod
    def fed_build_ready() -> bool:
        from core.infra.setup.core.install_runtime import fed_build_ready

        return fed_build_ready()

    @staticmethod
    def userspace_ready() -> bool:
        from core.infra.setup.core.install_runtime import userspace_ready

        return userspace_ready()

    @staticmethod
    def mark(
        profile: InstallProfileName,
        *,
        success: bool,
        failed_step_id: str = "",
        fingerprints: Optional[Dict[str, Any]] = None,
    ) -> None:
        from core.infra.setup.core.install_runtime import mark_runtime

        mark_runtime(
            profile,
            success=success,
            failed_step_id=failed_step_id,
            fingerprints=fingerprints,
        )


class ArtifactsNamespace:
    """安装产物工厂（userspace zip / 演示数据包）。"""

    @staticmethod
    def package_userspace(*, write_zip: bool = True) -> int:
        from core.infra.setup.core.scripts.init_userspace import package_init_userspace

        return package_init_userspace(write_zip=write_zip)

    @staticmethod
    def export_demo_data(argv: Optional[Sequence[str]] = None) -> int:
        from core.infra.setup.core.scripts.init_data.demo_data_exporter import main

        return main(list(argv) if argv is not None else None)


class MetaNamespace:
    """安装步骤元数据（UI wizard / CLI 步骤序）。"""

    @staticmethod
    def load_step_meta(*, ui_only: bool = True) -> List[Dict[str, Any]]:
        from core.infra.setup.core.meta_loader import load_setup_step_meta

        return load_setup_step_meta(ui_only=ui_only)


class TraceNamespace:
    """安装 / 启动埋点（失败不影响安装结果）。"""

    @staticmethod
    def install_complete(
        *,
        success: bool,
        entry: InstallEntry,
        error_code: Optional[str] = None,
    ) -> None:
        from core.infra.setup.core.trace_events import SetupTrace

        SetupTrace.install_complete(success=success, entry=entry, error_code=error_code)

    @staticmethod
    def app_start(*, entry: AppEntry, command: Optional[str] = None) -> None:
        from core.infra.setup.core.trace_events import SetupTrace

        SetupTrace.app_start(entry=entry, command=command)


class Setup:
    """安装域门面（Facade）。静态 API，勿实例化。"""

    env = EnvNamespace
    runtime = RuntimeNamespace
    artifacts = ArtifactsNamespace
    meta = MetaNamespace
    trace = TraceNamespace
    types = TypesNamespace
