#!/usr/bin/env python3
"""Entity Timeline 基准 Tag Worker：简化的市值档位分类（周频）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Sequence

from core.modules.data_contract.contracts import DataKey
from core.modules.strategy.services.data.helper import storage_key_for
from core.modules.tag.engines.shared.base_worker import BaseTagWorker
from core.modules.tag.engines.shared.staging.prior_values import parse_tag_value_scalar
from core.modules.tag.models.tag_model import TagModel

INDICATORS = storage_key_for(DataKey.STOCK_INDICATORS_DAILY)
TAG_NAME = "bench_cap_tier"
VALID_TIERS = frozenset({"micro", "low", "mid", "high"})


@dataclass(frozen=True)
class CapTierThresholds:
    """市值分档阈值（库内 total_market_value 单位：万元）。"""

    micro_cap_max_wan: float
    low_cap_max_wan: float
    mid_cap_max_wan: float

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> "CapTierThresholds":
        core = settings.get("core") or {}
        micro_yi = _float(core.get("micro_cap_max_threshold"), 10.0)
        low_yi = _float(core.get("low_cap_max_threshold"), 30.0)
        mid_yi = _float(core.get("mid_cap_max_threshold"), 100.0)
        if low_yi <= micro_yi:
            low_yi = micro_yi + 1.0
        if mid_yi <= low_yi:
            mid_yi = low_yi + 1.0
        return cls(
            micro_cap_max_wan=micro_yi * 10_000.0,
            low_cap_max_wan=low_yi * 10_000.0,
            mid_cap_max_wan=mid_yi * 10_000.0,
        )

    def classify(self, cap_wan: float) -> str:
        if cap_wan <= self.micro_cap_max_wan:
            return "micro"
        if cap_wan <= self.low_cap_max_wan:
            return "low"
        if cap_wan <= self.mid_cap_max_wan:
            return "mid"
        return "high"


def find_bar_on_date(
    rows: Sequence[Mapping[str, Any]],
    as_of_date: str,
) -> Optional[Dict[str, Any]]:
    target = str(as_of_date or "").strip()
    if not target:
        return None
    for row in reversed(rows or ()):
        dt = str(row.get("date") or "").strip()
        if dt == target:
            return dict(row)
        if dt and dt < target:
            break
    return None


class BenchmarkTimelineTagWorker(BaseTagWorker):
    """Entity Timeline 基准：检测市值档位变化，变化日写入 tag（周频）。"""

    def on_init(self) -> None:
        self._thresholds = CapTierThresholds.from_settings(self.settings)
        self._tier_tag_def: Optional[TagModel] = None
        for td in self.tag_definitions:
            if td.get_name() == TAG_NAME or td.tag_name == TAG_NAME:
                self._tier_tag_def = td
                break

        # 读取频率配置
        core = self.settings.get("core") or {}
        self._frequency = str(core.get("frequency", "daily")).strip().lower()
        self._target_weekday = int(core.get("weekday", 4))  # 默认周五

    def _should_calculate_on_date(self, as_of_date: str) -> bool:
        """检查是否应该在指定日期进行计算（周频控制）"""
        if self._frequency != "weekly":
            return True  # daily 模式：每天都计算

        try:
            dt = datetime.strptime(as_of_date, "%Y%m%d")
            return dt.weekday() == self._target_weekday
        except (ValueError, TypeError):
            return False

    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: TagModel,
    ) -> Optional[Dict[str, Any]]:
        if tag_definition.get_name() != TAG_NAME and tag_definition.tag_name != TAG_NAME:
            return None

        # 周频检查：只在指定星期几计算
        if not self._should_calculate_on_date(as_of_date):
            return None

        indicators = historical_data.get(INDICATORS) or []
        bar = find_bar_on_date(indicators, as_of_date)
        if bar is None:
            return None
        cap_wan = _float_or_none(bar.get("total_market_value"))
        if cap_wan is None:
            return None

        tier = self._thresholds.classify(cap_wan)
        if tier not in VALID_TIERS:
            return None

        last_tier = self._last_tier()
        if last_tier == tier:
            return None

        self.tracker["last_tier"] = tier
        return {"value": tier}

    def _last_tier(self) -> Optional[str]:
        cached = self.tracker.get("last_tier")
        if isinstance(cached, str) and cached in VALID_TIERS:
            return cached
        if self._tier_tag_def is None or self._tier_tag_def.id is None:
            return None
        raw = self.load_latest_tag_value_json(int(self._tier_tag_def.id))
        parsed = parse_tag_value_scalar(raw)
        if parsed in VALID_TIERS:
            self.tracker["last_tier"] = parsed
            return parsed
        return None


def _float(raw: Any, default: float) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _float_or_none(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
