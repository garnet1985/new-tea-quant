"""Series relation console API."""

from .api_base import series_relation_api_bp
from . import routes as _routes  # noqa: F401 — register handlers

__all__ = ["series_relation_api_bp"]
