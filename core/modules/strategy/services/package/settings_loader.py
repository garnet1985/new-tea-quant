"""Load strategy settings dict from disk without requiring a pre-imported userspace package."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict


def load_settings_dict_from_folder(strategy_folder: Path) -> Dict[str, Any]:
    """Read ``settings`` dict from ``settings.py`` under ``strategy_folder``."""
    folder = Path(strategy_folder)
    settings_file = folder / "settings.py"
    if not settings_file.is_file():
        raise FileNotFoundError(f"settings.py not found: {settings_file}")

    module_name = f"_ntq_strategy_settings_{folder.name}"
    spec = importlib.util.spec_from_file_location(module_name, settings_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load settings module: {settings_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    settings = getattr(module, "settings", None)
    if not isinstance(settings, dict):
        raise ValueError(f"settings.py must define a dict named settings: {settings_file}")
    return dict(settings)
