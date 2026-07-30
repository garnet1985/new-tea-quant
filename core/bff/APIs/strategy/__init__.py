"""Strategy domain BFF — HTTP only; domain logic in ``modules.strategy.launcher``."""

from .api_base import strategy_api_bp
from . import routes as _routes  # noqa: F401 — register handlers

__all__ = ["strategy_api_bp"]
