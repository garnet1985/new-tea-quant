"""扫描结果 → userspace opportunity adapters。

本文件:
- AdapterDispatcher: 按 settings.scanner.adapter_names 动态加载并 process
  边界: 负责 adapter 分发；不负责 scan 本身或默认 adapter 以外的存储策略
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.adapter import Adapter
from core.modules.adapter.contracts import BaseOpportunityAdapter
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity

logger = logging.getLogger(__name__)


@dataclass
class AdapterDispatcher:
    strategy_name: str

    def dispatch(
        self,
        adapter_names: List[str],
        opportunities: List[Opportunity],
        context: Dict[str, Any],
    ) -> None:
        if not adapter_names:
            BaseOpportunityAdapter.default_output(opportunities, context)
            return
        success = 0
        for name in adapter_names:
            cls = Adapter.load_class(name)
            if cls is None:
                continue
            try:
                cls().process(opportunities, context)
                success += 1
            except Exception as exc:
                logger.error(
                    "[AdapterDispatcher] adapter failed %s: %s",
                    name,
                    exc,
                    exc_info=True,
                )
        if success == 0:
            BaseOpportunityAdapter.default_output(opportunities, context)


__all__ = ["AdapterDispatcher"]
