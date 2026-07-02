"""枚举器引擎：EnabledStrategyInfo → 运行时上下文 → mode pipeline。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from core.modules.strategy.core.services.discovered_strategy import EnabledStrategyInfo

from .entity_based.pipeline import EntityBasedJobPipeline
from .slice_based.pipeline import SliceBasedJobPipeline


@dataclass
class EnumeratorEngine:
    """枚举编排入口（薄路由）。"""

    strategy_info: EnabledStrategyInfo

    def run(self) -> Dict[str, Any]:
        # 暂时使用strategy.settings判断execution_mode
        execution_mode = self.strategy_info.get_execution_mode()

        if execution_mode == "slice_based":
            return SliceBasedJobPipeline.run(self.strategy_info)

        if execution_mode == "entity_based":
            return EntityBasedJobPipeline.run(self.strategy_info)

        raise ValueError(f"不支持的execution_mode: {execution_mode}")

__all__ = ["EnumeratorEngine"]
