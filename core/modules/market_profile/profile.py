#!/usr/bin/env python3
"""MarketProfile 聚合：各 rule engine 编译结果的统一视图。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence, Tuple

from .rule_engines import REGISTRY
from .rule_engines.amplitude_limit.models import AmplitudeLimitCompiled
from .rule_engines.lot_size.models import LotSizeCompiled, LotSizeResolved
from .rule_engines.shared.base import CompiledRuleBase, MarketRuleEngineBase

logger = logging.getLogger(__name__)


class MarketProfile:
    def __init__(
        self,
        profile_id: str,
        *,
        name: str = "",
        description: str = "",
        compiled: Optional[Dict[str, CompiledRuleBase]] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.profile_id = profile_id
        self.name = name
        self.description = description
        self._compiled: Dict[str, CompiledRuleBase] = dict(compiled or {})
        self._raw = raw

    @classmethod
    def from_raw(cls, profile_id: str, raw: Dict[str, Any]) -> "MarketProfile":
        rules_block = raw.get("rules") if isinstance(raw.get("rules"), dict) else {}
        compiled: Dict[str, CompiledRuleBase] = {}
        known_keys = {engine_cls.rule_key for engine_cls in REGISTRY}

        for engine_cls in REGISTRY:
            if not issubclass(engine_cls, MarketRuleEngineBase):
                continue
            rule_key = engine_cls.rule_key
            block = rules_block.get(rule_key)
            if not isinstance(block, dict):
                continue
            engine = engine_cls()
            compiled[rule_key] = engine.parse(block)

        for rule_key in rules_block:
            if rule_key not in known_keys:
                logger.warning(
                    "market profile %r 含未知 rules.%s，已忽略",
                    profile_id,
                    rule_key,
                )

        return cls(
            profile_id,
            name=str(raw.get("name") or ""),
            description=str(raw.get("description") or ""),
            compiled=compiled,
            raw=raw,
        )

    def get_compiled(self, rule_key: str) -> Optional[CompiledRuleBase]:
        return self._compiled.get(rule_key)

    @property
    def amplitude_limit(self) -> Optional[AmplitudeLimitCompiled]:
        obj = self._compiled.get("amplitude_limit")
        return obj if isinstance(obj, AmplitudeLimitCompiled) else None

    @property
    def lot_size(self) -> Optional[LotSizeCompiled]:
        obj = self._compiled.get("lot_size")
        return obj if isinstance(obj, LotSizeCompiled) else None

    def resolve_limit_ratio(
        self,
        stock_id: str,
        status_tags: Optional[Sequence[str]] = None,
    ) -> float:
        amp = self.amplitude_limit
        if amp is None:
            raise KeyError("当前 profile 未配置 rules.amplitude_limit")
        return amp.resolve_ratio(stock_id, status_tags)

    def compute_limit_prices(
        self,
        stock_id: str,
        prev_close: float,
        status_tags: Optional[Sequence[str]] = None,
    ) -> Tuple[float, float]:
        amp = self.amplitude_limit
        if amp is None:
            raise KeyError("当前 profile 未配置 rules.amplitude_limit")
        return amp.compute_limit_prices(stock_id, prev_close, status_tags)

    def resolve_lot_rules(self, stock_id: str) -> LotSizeResolved:
        lot = self.lot_size
        if lot is None:
            raise KeyError("当前 profile 未配置 rules.lot_size")
        return lot.resolve(stock_id)

    def floor_buy_quantity(self, shares: int, stock_id: str) -> int:
        lot = self.lot_size
        if lot is None:
            raise KeyError("当前 profile 未配置 rules.lot_size")
        return lot.floor_buy_quantity(shares, stock_id)


__all__ = ["MarketProfile"]
