"""扫描结果 → Adapter 协议 → userspace 全局 enabled PostProcessor。

本文件:
- PostProcessDispatcher: 组装 ScanSessionReport 并执行所有 ``is_enabled`` 的 PostProcessor
  边界: 负责协议映射与调度；不负责 component 实现；不读策略 settings
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.post_process import PostProcess
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity

logger = logging.getLogger(__name__)


@dataclass
class PostProcessDispatcher:
    strategy_name: str
    strategy_version: str = ""
    goal: Optional[Dict[str, Any]] = None

    def dispatch(
        self,
        opportunities: List[Opportunity],
        context: Dict[str, Any],
    ) -> List[str]:
        scan_date = str((context or {}).get("date") or "").strip()
        session = PostProcess.build_session_report(
            scan_date=scan_date,
            strategy_name=self.strategy_name,
            opportunities=list(opportunities or []),
            goal=dict(self.goal or {}),
            strategy_version=str(self.strategy_version or ""),
        )
        try:
            return PostProcess.run_enabled_post_processors(session)
        except Exception as exc:
            logger.error(
                "[PostProcessDispatcher] enabled post_processors 失败: %s",
                exc,
                exc_info=True,
            )
            return []


__all__ = ["PostProcessDispatcher"]
