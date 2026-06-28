#!/usr/bin/env python3
"""策略根级 market_profile 设置。"""

from __future__ import annotations

from dataclasses import dataclass

from core.infra.project_context import ProjectContext

from core.modules.market_profile.constants import DEFAULT_PROFILE_ID, MARKETS_CONFIG_DIR

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategyMarketProfileSettings(SettingsBase):
    profile_id: str = DEFAULT_PROFILE_ID

    @classmethod
    def from_strategy_root(cls, root: dict) -> "StrategyMarketProfileSettings":
        if not isinstance(root, dict):
            root = {}
        raw = root.get("market_profile", DEFAULT_PROFILE_ID)
        pid = str(raw or DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID
        inst = cls(profile_id=pid)
        inst.apply_defaults()
        return inst

    def apply_defaults(self) -> None:
        self.profile_id = str(self.profile_id or DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID

    def validate(self) -> ValidationReport:
        self.apply_defaults()
        result = SettingsBase.new_validation()
        known = ProjectContext.discovery.discover_configs(MARKETS_CONFIG_DIR)
        if known and self.profile_id not in known:
            SettingsBase.add_critical(
                result,
                "market_profile",
                f"未知 market_profile {self.profile_id!r}；可用: {', '.join(known)}",
                suggested_fix=(
                    f'在 settings.py 中设置 "market_profile": "china_a_stock" 等，'
                    f"或于 userspace/system/config/markets/ 添加对应 JSON"
                ),
            )
        return result

    def to_dict(self) -> dict:
        return {"market_profile": self.profile_id}


__all__ = ["StrategyMarketProfileSettings"]
