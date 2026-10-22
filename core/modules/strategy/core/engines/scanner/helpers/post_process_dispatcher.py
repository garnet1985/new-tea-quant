"""扫描结果 → Adapter 协议 → userspace PostProcess。

本文件:
- PostProcessDispatcher: 组装 ScanSessionReport 并执行 scanner.post_process
  边界: 负责协议映射与调度；不负责 component 实现
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.post_process import PostProcess
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity

logger = logging.getLogger(__name__)

DEFAULT_POST_PROCESS = "console"


@dataclass
class PostProcessDispatcher:
    strategy_name: str
    strategy_version: str = ""
    goal: Optional[Dict[str, Any]] = None

    def dispatch(
        self,
        post_process_key: str,
        opportunities: List[Opportunity],
        context: Dict[str, Any],
    ) -> None:
        key = str(post_process_key or "").strip() or DEFAULT_POST_PROCESS
        scan_date = str((context or {}).get("date") or "").strip()
        session = PostProcess.build_session_report(
            scan_date=scan_date,
            strategy_name=self.strategy_name,
            opportunities=list(opportunities or []),
            goal=dict(self.goal or {}),
            strategy_version=str(self.strategy_version or ""),
        )
        try:
            PostProcess.run_post_processor(key, session)
        except Exception as exc:
            logger.error(
                "[PostProcessDispatcher] post_process '%s' 失败: %s",
                key,
                exc,
                exc_info=True,
            )


__all__ = ["DEFAULT_POST_PROCESS", "PostProcessDispatcher"]
