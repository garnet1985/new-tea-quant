#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import logging

from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.engines.shared.helpers.strategy_runtime import resolve_worker_class

logger = logging.getLogger(__name__)


@dataclass
class SimulatorHooksDispatcher:
    strategy_name: str

    def __post_init__(self) -> None:
        self._worker_class: Optional[type[BaseStrategyWorker]] = None
        self._worker_instance: Optional[BaseStrategyWorker] = None

    def _load_worker_class(self) -> Optional[type[BaseStrategyWorker]]:
        if self._worker_class is not None:
            return self._worker_class
        try:
            self._worker_class = resolve_worker_class(self.strategy_name)
            return self._worker_class
        except Exception:
            return None

    def _get_worker_instance(self) -> Optional[BaseStrategyWorker]:
        if self._worker_instance is not None:
            return self._worker_instance
        worker_class = self._load_worker_class()
        if worker_class is None:
            return None
        dummy_payload: dict[str, Any] = {
            "stock_id": "DUMMY",
            "execution_mode": "scan",
            "strategy_name": self.strategy_name,
            "settings": {},
        }
        try:
            self._worker_instance = worker_class(dummy_payload)  # type: ignore[call-arg]
        except Exception as exc:
            logger.warning("[SimulatorHooksDispatcher] init worker failed: %s", exc)
            self._worker_instance = None
        return self._worker_instance

    def call_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> Any:
        instance = self._get_worker_instance()
        if instance is None:
            return None
        hook_method = getattr(instance, hook_name, None)
        if hook_method is None:
            return None
        base_method = getattr(BaseStrategyWorker, hook_name, None)
        if base_method is not None and getattr(hook_method, "__func__", None) is base_method:  # type: ignore[attr-defined]
            return None
        try:
            return hook_method(*args, **kwargs)
        except Exception as exc:
            logger.warning("[SimulatorHooksDispatcher] hook failed %s: %s", hook_name, exc)
            return None


__all__ = ["SimulatorHooksDispatcher"]
