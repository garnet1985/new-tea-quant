#!/usr/bin/env python3
"""DbCache 可配置常量（与 ``docs/db-cache-service.md`` §7 对齐）。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

# 每个 strategy_name 最多保留的快照行数；超出则删最早 version
MAX_SNAPSHOT_ROWS_PER_STRATEGY: int = 50

# 同一快照行累计 UPDATE 超过此次数则触发删行；持久化路径按指纹重建新行（见 ``audit.result_report_audit``）
MAX_SNAPSHOT_ROW_UPDATES: int = 10


@lru_cache(maxsize=1)
def read_strategy_module_version() -> str:
    """读取 ``core/modules/strategy/module_info.yaml`` 的 ``version``（用于 env 指纹）。"""
    here = Path(__file__).resolve()
    strategy_root = here.parents[3]
    info_path = strategy_root / "module_info.yaml"
    if not info_path.is_file():
        return "0.0.0"
    try:
        raw = yaml.safe_load(info_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            ver = raw.get("version")
            if ver is not None:
                return str(ver).strip() or "0.0.0"
    except Exception:
        pass
    return "0.0.0"


def derive_run_mode(normalized_settings: Dict[str, Any]) -> str:
    """``sampling`` | ``full`` — 与 ``settings_resolver.resolve_sampling_is_used`` 一致。"""
    from .finger_print.settings_resolver import resolve_sampling_is_used

    return "sampling" if resolve_sampling_is_used(dict(normalized_settings or {})) else "full"
