"""Strategy domain: workbench + scan (+ package routes on workbench)."""

from .blueprint import strategy_api_bp

# Register route handlers onto strategy_api_bp
from .workbench import routes as _workbench_routes  # noqa: F401,E402
from .scan import routes as _scan_routes  # noqa: F401,E402

# Back-compat aliases (tests / old imports)
strategy_workbench_api_bp = strategy_api_bp
strategy_scan_api_bp = strategy_api_bp

__all__ = [
    "strategy_api_bp",
    "strategy_workbench_api_bp",
    "strategy_scan_api_bp",
]
