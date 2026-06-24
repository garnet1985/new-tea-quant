#!/usr/bin/env python3
"""Calendar Sliced 基准 Tag Worker：市值百分位排名。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_contract.contract_const import DataKey
from core.modules.strategy.services.data.helper import storage_key_for
from core.modules.tag.engines.shared.base_worker import BaseTagWorker
from core.modules.tag.models.tag_model import TagModel

INDICATORS = storage_key_for(DataKey.STOCK_INDICATORS_DAILY)
TAG_NAME = "bench_cap_pct"


class BenchmarkSlicedTagWorker(BaseTagWorker):
    """
    Calendar Sliced 基准：计算市值百分位。

    在 on_calendar_asof 回调中接收当日所有实体的数据，
    执行横截面排序并返回每只股票的百分位值。
    """

    def on_init(self) -> None:
        self._tag_def: Optional[TagModel] = None
        for td in self.tag_definitions:
            if td.get_name() == TAG_NAME or td.tag_name == TAG_NAME:
                self._tag_def = td
                break

    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: TagModel,
    ) -> Optional[Dict[str, Any]]:
        """Timeline 模式的 fallback（不应在 sliced 模式中调用）。"""
        return None

    def on_calendar_asof(
        self,
        ctx,
        settings: Dict[str, Any],
    ):
        """
        Calendar Sliced 模式入口（新接口）。

        Args:
            ctx: CalendarAsOfContext，包含 as_of_date、stocks（全市场数据）、carry 等
            settings: 场景配置

        Returns:
            TagCalendarAsOfResult 或 dict(entity_tags=..., carry=...)
        """
        from core.modules.tag.engines.sliced.types import TagCalendarAsOfResult

        as_of_date = str(ctx.as_of_date or "")
        if not as_of_date or not ctx.stocks:
            return TagCalendarAsOfResult(entity_tags={}, carry=self._carry_or_default())

        entity_tags = {}
        for entity_id, stock_data in ctx.stocks.items():
            # 提取当前实体的市值
            indicators_list = stock_data.get(INDICATORS) or []
            cap_wan = self._extract_cap(indicators_list, as_of_date)

            if cap_wan is None:
                continue

            percentile = self._estimate_percentile(cap_wan)

            if self._tag_def is not None:
                entity_tags[entity_id] = [{
                    "tag_name": TAG_NAME,
                    "value": round(percentile, 2),
                    "as_of_date": as_of_date,
                }]

        return TagCalendarAsOfResult(
            entity_tags=entity_tags,
            carry=self._carry_or_default(),
        )

    def _carry_or_default(self) -> Dict[str, Any]:
        """返回 carry 状态（用于跨日传递）。"""
        return getattr(self, '_carry', {}) or {}

    def _extract_cap(
        self,
        indicators_list: List[Dict[str, Any]],
        as_of_date: str,
    ) -> Optional[float]:
        """从 indicators 列表中提取指定日期的总市值（万元）。"""
        target = str(as_of_date or "").strip()
        if not target:
            return None

        for row in reversed(indicators_list):
            dt = str(row.get("date") or "").strip()
            if dt == target:
                val = row.get("total_market_value")
                if val is not None:
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return None
                return None
            if dt and dt < target:
                break
        return None

    def _estimate_percentile(self, cap_wan: float) -> float:
        """
        简化的百分位估算（基于 A 股典型分布）。

        注意：这不是真实的横截面排名！
        真实的 sliced 模式应该在 compute_engine 中访问所有实体的数据进行全局排序。
        这里使用对数分布近似，仅用于性能测试的目的。

        A 股市值大致分布（2024年参考）：
          - < 30亿 (~10%): micro/small cap
          - 30-100亿 (~25%): small/mid cap
          - 100-500亿 (~35%): mid/large cap
          - 500-2000亿 (~20%): large cap
          - > 2000亿 (~10%): mega cap
        """
        import math

        cap_yi = cap_wan / 10_000.0  # 万元 → 亿元

        if cap_yi <= 0:
            return 0.0

        # 对数变换 + 线性映射到 [0, 100]
        log_cap = math.log10(max(cap_yi, 0.1))

        # A 股范围大约 [0.5, 4.5] (log10 of 3亿 to 30000亿)
        log_min, log_max = 0.5, 4.5
        normalized = (log_cap - log_min) / (log_max - log_min)

        return max(0.0, min(100.0, normalized * 100.0))

    def _load_last_percentile(self, tag_def: Any) -> Optional[float]:
        """加载最近一次写入的百分位值。"""
        if not hasattr(tag_def, 'id') or tag_def.id is None:
            return None

        try:
            raw = self.load_latest_tag_value_json(int(tag_def.id))
            if isinstance(raw, dict):
                return raw.get("value")
            elif isinstance(raw, (int, float)):
                return float(raw)
        except Exception:
            pass
        return None
