#!/usr/bin/env python3
"""Resolve market profile id from job payload — no strategy_settings / enumerator imports."""

from __future__ import annotations

from typing import Any, Dict

from core.modules.market_profile.constants import DEFAULT_PROFILE_ID


def resolve_market_profile_id(
    job_payload: Dict[str, Any],
    *,
    settings_market_profile: str = "",
) -> str:
    """Flow 注入 ``market_profile_id`` 优先；否则用 settings 根级字符串。"""
    pid = str((job_payload or {}).get("market_profile_id") or "").strip()
    if pid:
        return pid
    fallback = str(settings_market_profile or "").strip()
    return fallback or DEFAULT_PROFILE_ID


__all__ = ["resolve_market_profile_id"]
