"""扫描结果 → userspace opportunity adapters。

本文件:
- AdapterDispatcher: 按 settings.scanner.adapter_names 动态加载并 process
  边界: 负责 adapter 分发；把 price 历史统计推进 context（adapter 不回读产物）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.adapter import Adapter
from core.modules.adapter.contracts import BaseOpportunityAdapter
from core.modules.strategy.core.engines.scanner.helpers.price_history_enrichment import (
    build_price_history_for_adapter,
)
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
        enriched = dict(context or {})
        if "price_history" not in enriched:
            stock_ids = [str(getattr(o, "stock_id", "") or "") for o in opportunities]
            enriched["price_history"] = build_price_history_for_adapter(
                self.strategy_name,
                stock_ids,
            )

        if not adapter_names:
            BaseOpportunityAdapter.default_output(opportunities, enriched)
            return
        success = 0
        for name in adapter_names:
            cls = Adapter.load_class(name)
            if cls is None:
                continue
            try:
                cls().process(opportunities, enriched)
                success += 1
            except Exception as exc:
                logger.error(
                    "[AdapterDispatcher] adapter failed %s: %s",
                    name,
                    exc,
                    exc_info=True,
                )
        if success == 0:
            BaseOpportunityAdapter.default_output(opportunities, enriched)


__all__ = ["AdapterDispatcher"]
