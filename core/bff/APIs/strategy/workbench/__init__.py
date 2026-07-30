"""Strategy workbench API package."""

# Routes register onto shared strategy_api_bp when this package is imported.
from . import routes as _routes  # noqa: F401

__all__: list[str] = []
