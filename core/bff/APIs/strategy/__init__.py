"""Strategy domain BFF — HTTP via ``routes/`` (catalog / package / report / settings / version / runner)."""

from .api_base import strategy_api_bp
from . import routes as _routes  # noqa: F401 — register handlers

__all__ = ["strategy_api_bp"]
