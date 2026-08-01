"""
BFF APIs — business-domain packages under platform / data / strategy / tag.
"""

from .platform import (
    health_api_bp,
    runtime_api_bp,
    setup_api_bp,
    SetupService,
    SetupRuntimeManager,
    settings_api_bp,
)
from .data import data_source_api_bp, data_contract_api_bp
from .strategy import strategy_api_bp
from .tag import tag_api_bp

__all__ = [
    "SetupService",
    "SetupRuntimeManager",
    "health_api_bp",
    "runtime_api_bp",
    "setup_api_bp",
    "settings_api_bp",
    "data_source_api_bp",
    "data_contract_api_bp",
    "strategy_api_bp",
    "tag_api_bp",
]
