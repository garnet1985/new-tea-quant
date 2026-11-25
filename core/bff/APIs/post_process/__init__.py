"""Post-process console API package."""

from .api_base import post_process_api_bp
from . import routes as _routes  # noqa: F401 — register handlers

__all__ = ["post_process_api_bp"]
