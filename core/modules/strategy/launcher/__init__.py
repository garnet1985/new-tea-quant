"""Strategy UI launchers — settings / snapshots / run / scan.

Report / stock detail / cache clear live in ``core.bff.APIs.strategy.routes.report``.
Consumers: ``core.bff.APIs.strategy.stack`` (remaining).
"""

from .scanner_run import (
    get_scan_page_context,
    get_scan_progress,
    get_scan_readiness,
    trigger_strategy_scan_run,
)
from .settings_options import StrategySettingsOptions
from .workbench_apply_settings import WorkbenchApplySettings
from .workbench_run import WorkbenchRunLauncher
from .workbench_snapshots import WorkbenchSnapshots

__all__ = [
    "StrategySettingsOptions",
    "WorkbenchApplySettings",
    "WorkbenchRunLauncher",
    "WorkbenchSnapshots",
    "get_scan_page_context",
    "get_scan_progress",
    "get_scan_readiness",
    "trigger_strategy_scan_run",
]
