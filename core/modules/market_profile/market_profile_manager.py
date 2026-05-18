#!/usr/bin/env python3
"""对外入口：加载、缓存、调度 rule engines。"""

from __future__ import annotations

from typing import Optional

from .profile import MarketProfile


class MarketProfileManager:
    pass


def get_market_profile(profile_id: Optional[str] = None) -> MarketProfile:
    pass


__all__ = ["MarketProfileManager", "get_market_profile"]
