"""Budgeted flush of the local trace queue."""

from __future__ import annotations

import logging
import time
from typing import Optional, Union

from ...contracts import FlushBudget
from .client_service import TraceClientService
from .config_service import TraceConfigService
from .queue_service import TraceQueueService

logger = logging.getLogger(__name__)

_BUDGETS = {
    FlushBudget.STANDARD.value: {"max_sec": 1.0, "max_events": 5},
    FlushBudget.EXTREME.value: {"max_sec": 2.0, "max_events": 10},
}


class TraceFlushService:
    """Drain queued events under a time/count budget. Never raises."""

    @staticmethod
    def resolve_budget(name: Optional[Union[str, FlushBudget]] = None) -> str:
        cfg = TraceConfigService.load()
        if isinstance(name, FlushBudget):
            if name in {FlushBudget.STANDARD, FlushBudget.EXTREME}:
                return name.value
            name = None
        if name in {FlushBudget.STANDARD.value, FlushBudget.EXTREME.value}:
            return str(name)
        depth = TraceQueueService.depth()
        if depth >= int(cfg.extreme_depth or 20):
            return FlushBudget.EXTREME.value
        return FlushBudget.STANDARD.value

    @staticmethod
    def flush(*, budget: Optional[Union[str, FlushBudget]] = None) -> int:
        try:
            cfg = TraceConfigService.load()
            if not cfg.enabled:
                return 0
            url = str(cfg.target_url or "")
            if not url:
                return 0

            chosen = TraceFlushService.resolve_budget(budget)
            limits = _BUDGETS[chosen]
            max_sec = float(limits["max_sec"])
            max_events = int(limits["max_events"])
            timeout = float(cfg.timeout_sec or 2.0)
            max_attempts = int(cfg.max_attempts or 10)

            started = time.monotonic()
            sent = 0
            while sent < max_events and (time.monotonic() - started) < max_sec:
                claimed = TraceQueueService.claim_next()
                if claimed is None:
                    break
                path, event = claimed
                ok = TraceClientService.post(url, event, timeout_sec=timeout)
                if ok:
                    TraceQueueService.complete(path)
                    sent += 1
                else:
                    TraceQueueService.requeue(path, event, max_attempts=max_attempts)
                    break
            return sent
        except Exception as exc:
            logger.debug("trace flush failed: %s", exc)
            return 0
