"""从策略目录读 ``attribution.py`` → raw dict。"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional

from core.modules.strategy.core.services.discovery.path_rules import StrategyPathRules

ATTRIBUTION_FILE_NAME = "attribution.py"


def load_attribution_dict(
    strategy_folder: Path,
    *,
    strategy_key: Optional[str] = None,
) -> Dict[str, Any]:
    folder = Path(strategy_folder)
    attr_file = folder / ATTRIBUTION_FILE_NAME
    if not attr_file.is_file():
        raise FileNotFoundError(f"attribution.py not found: {attr_file}")

    key = str(strategy_key or folder.name).strip() or folder.name
    module_name = StrategyPathRules.strategy_module_id(key, suffix="attribution")
    spec = importlib.util.spec_from_file_location(module_name, attr_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load attribution module: {attr_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = getattr(module, "attribution", None)
    if not isinstance(payload, dict):
        raise ValueError(f"attribution.py 必须定义 dict attribution: {attr_file}")
    return dict(payload)
