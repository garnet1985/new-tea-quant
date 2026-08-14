"""Load strategy settings dict from disk without requiring a pre-imported userspace package."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional

from core.modules.strategy.core.services.discovery.path_rules import StrategyPathRules


def load_settings_dict_from_folder(
    strategy_folder: Path,
    *,
    strategy_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Read ``settings`` dict from ``settings.py`` under ``strategy_folder``."""
    folder = Path(strategy_folder)
    settings_file = folder / "settings.py"
    if not settings_file.is_file():
        raise FileNotFoundError(f"settings.py not found: {settings_file}")

    key = str(strategy_key or folder.name).strip() or folder.name
    module_name = StrategyPathRules.strategy_module_id(key, suffix="settings")
    spec = importlib.util.spec_from_file_location(module_name, settings_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load settings module: {settings_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    settings = getattr(module, "settings", None)
    if not isinstance(settings, dict):
        raise ValueError(f"settings.py must define a dict named settings: {settings_file}")
    return dict(settings)


__all__ = ["load_settings_dict_from_folder"]
