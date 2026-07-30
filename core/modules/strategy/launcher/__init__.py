"""Strategy UI launchers — catalog / settings / snapshots / run / reports / scan.

Consumers: ``core.bff.APIs.strategy`` (workbench + scan stacks)
"""

from .scanner_run import (
    get_scan_page_context,
    get_scan_progress,
    get_scan_readiness,
    trigger_strategy_scan_run,
)
from .settings_options import StrategySettingsOptions
from .workbench_apply_settings import WorkbenchApplySettings
from .workbench_cache_clear import WorkbenchCacheClear
from .workbench_reports import WorkbenchReports
from .workbench_run import WorkbenchRunLauncher
from .workbench_snapshots import WorkbenchSnapshots
from .workbench_stock_detail import WorkbenchStockDetail

__all__ = [
    "StrategySettingsOptions",
    "WorkbenchApplySettings",
    "WorkbenchCacheClear",
    "WorkbenchReports",
    "WorkbenchRunLauncher",
    "WorkbenchSnapshots",
    "WorkbenchStockDetail",
    "get_scan_page_context",
    "get_scan_progress",
    "get_scan_readiness",
    "trigger_strategy_scan_run",
]
