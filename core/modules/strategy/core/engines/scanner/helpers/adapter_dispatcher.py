"""扫描结果 → userspace opportunity adapters。

本文件:
- AdapterDispatcher: 按 settings.scanner.adapter_names 动态加载并 process
  边界: 负责 adapter 分发；不负责 scan 本身或默认 adapter 以外的存储策略
"""

from __future__ import annotations

import importlib
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from core.modules.adapter import BaseOpportunityAdapter
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
            cls = self._load_adapter_class(name)
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

    def _load_adapter_class(
        self, adapter_name: str
    ) -> Optional[Type[BaseOpportunityAdapter]]:
        module_path = f"userspace.extensions.adapters.{adapter_name}.adapter"
        try:
            module = importlib.import_module(module_path)
        except Exception:
            return None
        for _, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseOpportunityAdapter)
                and obj is not BaseOpportunityAdapter
            ):
                return obj
        return None


__all__ = ["AdapterDispatcher"]
