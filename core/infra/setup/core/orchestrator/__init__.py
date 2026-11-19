"""安装编排：CLI / UI / session。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .options import CliInstallOptions

if TYPE_CHECKING:
    from .orchestrator import InstallOrchestrator

__all__ = ["InstallOrchestrator", "CliInstallOptions"]


def __getattr__(name: str):
    if name == "InstallOrchestrator":
        from .orchestrator import InstallOrchestrator as _InstallOrchestrator

        return _InstallOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
