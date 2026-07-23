"""Sampling settings (``settings.sampling``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet

from .settings_base import SettingsBase
from .validation_report import ValidationReport

_KNOWN_STRATEGIES: FrozenSet[str] = frozenset(
    {
        "uniform",
        "stratified",
        "random",
        "weighted",
        "continuous",
        "pool",
        "blacklist",
    }
)


@dataclass
class SamplingSettings(SettingsBase):
    """``settings.sampling``：股票池采样（``use_sampling=False`` 时可整段省略）。"""

    raw_settings: Dict[str, Any]

    @property
    def sampling(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "sampling")

    @property
    def use_sampling(self) -> bool:
        return bool(self.sampling.get("use_sampling", False))

    @property
    def strategy(self) -> str:
        raw = str(self.sampling.get("strategy") or "uniform").strip()
        return raw or "uniform"

    @property
    def sampling_amount(self) -> int:
        try:
            return max(1, int(self.sampling.get("sampling_amount") or 10))
        except (TypeError, ValueError):
            return 10

    def apply_defaults(self) -> None:
        # 未写 sampling 块时不强制写入；use_sampling 默认视为 False
        if "sampling" not in self.raw_settings:
            return
        if not isinstance(self.raw_settings["sampling"], dict):
            self.raw_settings["sampling"] = {}
        block = self.raw_settings["sampling"]
        if "use_sampling" not in block:
            block["use_sampling"] = False
        if block.get("use_sampling") and "strategy" not in block:
            block["strategy"] = "uniform"
        if block.get("use_sampling") and "sampling_amount" not in block:
            block["sampling_amount"] = 10

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()

        if "sampling" not in self.raw_settings:
            return report

        if not isinstance(self.raw_settings.get("sampling"), dict):
            SettingsBase.add_critical(
                report,
                "sampling",
                "sampling must be dict",
                suggested_fix='Set sampling to {} or omit the block',
            )
            return report

        if self.sampling.get("stock_pool"):
            SettingsBase.add_critical(
                report,
                "sampling.stock_pool",
                "sampling.stock_pool is removed; use strategy='pool' with sampling.pool",
                suggested_fix=(
                    '{"use_sampling": true, "strategy": "pool", '
                    '"pool": {"stock_ids": ["000001.SZ"]}}'
                ),
            )

        if not self.use_sampling:
            return report

        if self.strategy not in _KNOWN_STRATEGIES:
            SettingsBase.add_critical(
                report,
                "sampling.strategy",
                f"unknown sampling strategy: {self.strategy!r}",
                suggested_fix=f"One of: {sorted(_KNOWN_STRATEGIES)}",
            )

        if self.strategy == "pool":
            pool = self.sampling.get("pool")
            if not isinstance(pool, dict):
                SettingsBase.add_critical(
                    report,
                    "sampling.pool",
                    "strategy='pool' requires sampling.pool dict",
                    suggested_fix='{"stock_ids": [...]} or {"file": "stock_lists/pool.txt"}',
                )
            else:
                ids = pool.get("stock_ids") or []
                file_path = str(pool.get("file") or "").strip()
                if not ids and not file_path:
                    SettingsBase.add_critical(
                        report,
                        "sampling.pool",
                        "pool requires stock_ids or file",
                        suggested_fix='{"stock_ids": ["000001.SZ"]} or {"file": "..."}',
                    )

        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        if "sampling" not in self.raw_settings:
            return {}
        return dict(self.sampling)


__all__ = ["SamplingSettings"]
