#!/usr/bin/env python3
"""各 Simulator flow 与 DbCache 指纹对齐共用的 stock_ids / raw_settings 解析。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.modules.strategy.services.data.output.enumerator_output_service import (
    EnumeratorOutputWriterService,
)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
        StrategySettingsView,
    )


def stock_ids_for_db_cache_fingerprint(
    output_version_dir: Path,
    *,
    fallback_ids: List[str],
) -> List[str]:
    """
    env 指纹中的 ``stock_ids`` 与枚举 run 一致：优先读 ``0_stock_ref.json`` /
    ``0_scope_stock_ids.txt``，否则 metadata 内嵌，再回退 ``fallback_ids``。
    """
    ids = EnumeratorOutputWriterService.read_scope_stock_ids(output_version_dir)
    if ids:
        return ids
    return sorted({str(s) for s in fallback_ids if s})


def raw_settings_for_db_cache_fingerprint(
    base_settings: "StrategySettingsView",
    strategy_info: Optional["DiscoveredStrategy"],
) -> Dict[str, Any]:
    """与 ``StrategyFingerprintManager.canonicalize_settings`` 对齐，失败回退 view。"""
    if strategy_info is not None:
        try:
            from core.modules.strategy.services.launcher.run_service import (
                StrategyFingerprintManager,
            )

            return StrategyFingerprintManager.canonicalize_settings(
                dict(strategy_info.settings.to_dict())
            )
        except Exception:
            pass
    return dict(base_settings.to_dict())


__all__ = [
    "raw_settings_for_db_cache_fingerprint",
    "stock_ids_for_db_cache_fingerprint",
]
