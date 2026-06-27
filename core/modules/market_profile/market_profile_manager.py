#!/usr/bin/env python3
"""对外入口：加载、缓存、调度 rule engines。"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

from core.infra.project_context import ProjectContext
from core.infra.project_context.discovery_manager import DiscoveryManager
from core.infra.project_context.config_merge_policies import merge_market_profile_dicts

from .constants import DEFAULT_PROFILE_ID, MARKETS_CONFIG_DIR
from .profile import MarketProfile
from .rule_engines.lot_size.models import LotSizeResolved


class MarketProfileManager:
    def __init__(self) -> None:
        self._cache: Dict[str, MarketProfile] = {}

    def get_profile(self, profile_id: Optional[str] = None) -> MarketProfile:
        pid = str(profile_id or DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID
        known = DiscoveryManager.discover_configs(MARKETS_CONFIG_DIR)
        if known and pid not in known:
            raise ValueError(
                f"未知 market_profile {pid!r}；可用: {', '.join(known)}"
            )
        if pid not in self._cache:
            raw = DiscoveryManager.load_overridable_config(
                MARKETS_CONFIG_DIR,
                pid,
                merge_fn=merge_market_profile_dicts,
            )
            self._cache[pid] = MarketProfile.from_raw(pid, raw)
        return self._cache[pid]

    def clear_cache(self) -> None:
        self._cache.clear()

    def resolve_limit_ratio(
        self,
        stock_id: str,
        *,
        profile_id: Optional[str] = None,
        status_tags: Optional[Sequence[str]] = None,
    ) -> float:
        return self.get_profile(profile_id).resolve_limit_ratio(
            stock_id, status_tags
        )

    def compute_limit_prices(
        self,
        stock_id: str,
        prev_close: float,
        *,
        profile_id: Optional[str] = None,
        status_tags: Optional[Sequence[str]] = None,
    ) -> Tuple[float, float]:
        return self.get_profile(profile_id).compute_limit_prices(
            stock_id, prev_close, status_tags
        )

    def resolve_lot_rules(
        self, stock_id: str, *, profile_id: Optional[str] = None
    ) -> LotSizeResolved:
        return self.get_profile(profile_id).resolve_lot_rules(stock_id)

    def floor_buy_quantity(
        self,
        shares: int,
        stock_id: str,
        *,
        profile_id: Optional[str] = None,
    ) -> int:
        return self.get_profile(profile_id).floor_buy_quantity(shares, stock_id)


_default_manager = MarketProfileManager()


def get_market_profile(profile_id: Optional[str] = None) -> MarketProfile:
    return _default_manager.get_profile(profile_id)


def clear_market_profile_cache() -> None:
    _default_manager.clear_cache()


__all__ = [
    "MarketProfileManager",
    "clear_market_profile_cache",
    "get_market_profile",
]
