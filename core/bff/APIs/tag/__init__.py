"""Tag console API package."""

from .api_base import tag_api_bp
from . import routes as _routes  # noqa: F401 — register handlers

__all__ = ["tag_api_bp"]
