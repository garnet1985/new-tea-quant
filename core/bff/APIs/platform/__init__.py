"""Platform domain: health, runtime, setup, app_settings."""

from .health import health_api_bp
from .runtime import runtime_api_bp
from .setup import setup_api_bp, SetupService, SetupRuntimeManager
from .app_settings import settings_api_bp

__all__ = [
    "health_api_bp",
    "runtime_api_bp",
    "setup_api_bp",
    "SetupService",
    "SetupRuntimeManager",
    "settings_api_bp",
]
