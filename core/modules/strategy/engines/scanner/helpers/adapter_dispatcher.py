#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional
import importlib
import inspect
import logging

from core.modules.adapter import BaseOpportunityAdapter
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity

logger = logging.getLogger(__name__)


@dataclass
class AdapterDispatcher:
    strategy_name: str

    def dispatch(
        self,
        adapter_names: List[str],
        opportunities: List[Opportunity],
        context: dict[str, Any],
    ) -> None:
        success_count = 0
        if not adapter_names:
            BaseOpportunityAdapter.default_output(opportunities, context)
            return
        for adapter_name in adapter_names:
            adapter_class = self._load_adapter_class(adapter_name)
            if adapter_class is None:
                continue
            try:
                adapter = adapter_class()
                adapter.process(opportunities, context)
                success_count += 1
            except Exception as exc:
                logger.error("[AdapterDispatcher] adapter failed %s: %s", adapter_name, exc, exc_info=True)
        if success_count == 0:
            BaseOpportunityAdapter.default_output(opportunities, context)

    def _load_adapter_class(self, adapter_name: str) -> Optional[type[BaseOpportunityAdapter]]:
        module_path = f"userspace.adapters.{adapter_name}.adapter"
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
