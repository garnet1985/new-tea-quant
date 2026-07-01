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

    strategy: EnabledStrategyInfo
    userspace_root: Path = field(default_factory=lambda: Path("userspace"))
    user_settings: Optional[Dict[str, Any]] = None

    def run(self) -> Dict[str, Any]:
        # TODO: 构建运行时上下文（计算version/fingerprint/output等）
        # 暂时使用strategy.settings判断execution_mode
        execution_mode = self.strategy.settings.get("core", {}).get("execution_mode", "entity_based")

        if execution_mode == "slice_based":
            # TODO: 传递运行时上下文给SliceBasedJobPipeline
            return SliceBasedJobPipeline.run(self.strategy, self.userspace_root)

        return EntityBasedJobPipeline.run(self.strategy, self.userspace_root)


__all__ = ["EnumeratorEngine"]
