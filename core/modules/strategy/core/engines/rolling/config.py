"""从策略目录读 ``rolling.py``，窗口不进执行指纹。"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.services.discovery.path_rules import StrategyPathRules

ROLLING_FILE_NAME = "rolling.py"


def load_rolling_windows(
    strategy_folder: Path,
    *,
    strategy_key: Optional[str] = None,
) -> Tuple[Dict[str, str], ...]:
    """读出窗口列表；没有文件、空列表或重复窗口时拒绝。"""
    folder = Path(strategy_folder)
    path = folder / ROLLING_FILE_NAME
    if not path.is_file():
        raise FileNotFoundError(f"找不到 rolling.py: {path}")

    key = str(strategy_key or folder.name).strip() or folder.name
    module_name = StrategyPathRules.strategy_module_id(key, suffix="rolling")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"无法加载 rolling.py: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = getattr(module, "rolling", None)
    if not isinstance(payload, Mapping):
        raise ValueError(f"rolling.py 必须定义 dict rolling: {path}")
    return _parse_windows(payload.get("windows"), path)


def _parse_windows(raw: object, path: Path) -> Tuple[Dict[str, str], ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise ValueError(
            f"{path} 的 rolling.windows 须为非空 list，"
            '例如 [{"start": "20240101", "end": "20241231"}]'
        )
    seen: List[Tuple[str, str]] = []
    out: List[Dict[str, str]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"rolling.windows[{index}] 须为含 start / end 的 dict")
        start = str(item.get("start") or "").strip()
        end = str(item.get("end") or "").strip()
        if not start or not end:
            raise ValueError(f"rolling.windows[{index}] 的 start 与 end 必填")
        if start > end:
            raise ValueError(f"rolling.windows[{index}] 的 start {start} > end {end}")
        pair = (start, end)
        if pair in seen:
            raise ValueError(f"rolling.windows[{index}] 窗口重复 {start}-{end}")
        seen.append(pair)
        out.append({"start": start, "end": end})
    return tuple(out)
