#!/usr/bin/env python3
"""
Example Strategy Worker (activity_high gated)

基于 userspace/strategies/example 的逻辑：
- 仍然用 RSI(14) 超卖作为价格条件
- 但额外增加一个“门槛”：只有当 Tag 场景 activity-ratio20 的 activity_high 为 True 时才认为是机会
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import json
import logging

from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.models.opportunity import Opportunity

logger = logging.getLogger(__name__)


class ExampleActivityHighStrategyWorker(BaseStrategyWorker):
    def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Opportunity]:
        core = settings.get("core", {}) or {}

        # 1) Tag gate：activity_high 必须为 True
        gate_tag_name = core.get("activity_gate_tag_name", "activity_high")
        tags = data.get("tags", []) or []

        if not self._is_tag_true(tags, gate_tag_name):
            return None

        # 2) 原 example 条件：RSI 超卖
        rsi_length = int(settings["data"]["indicators"]["rsi"][0].get("period"))
        klines = data.get("klines", [])
        if not klines or len(klines) < rsi_length:
            return None

        latest_kline = klines[-1]
        rsi_field = f"rsi{rsi_length}"
        latest_rsi = latest_kline.get(rsi_field)
        if latest_rsi is None:
            return None

        if latest_rsi >= core.get("rsi_oversold_threshold", 20):
            return None

        return Opportunity(
            stock=self.stock_info,
            record_of_today=latest_kline,
            extra_fields={
                "rsi_value": latest_rsi,
                "tag_gate": gate_tag_name,
            },
        )

    @staticmethod
    def _is_tag_true(tag_rows: Any, tag_name: str) -> bool:
        """
        Tag 场景只记录变化（delta log），因此需要从 <= today 的事件中取“最后一次状态”。

        data['tags'] 来自 TagDataService.load_values_for_entity，记录结构包含：
        - tag_name
        - as_of_date
        - json_value: {"value": true/false}（可能是 dict，也可能是 json string）
        """
        if not tag_rows:
            return False

        # tags 已通过游标裁剪到 “today 及之前”，这里直接从后往前找最新的该 tag 事件
        for row in reversed(tag_rows):
            if (row.get("tag_name") or row.get("name")) != tag_name:
                continue

            raw = row.get("json_value")
            if raw is None or raw == "":
                return False

            payload: Dict[str, Any]
            if isinstance(raw, dict):
                payload = raw
            else:
                try:
                    payload = json.loads(raw) if isinstance(raw, str) else {}
                except Exception:
                    payload = {}

            v = payload.get("value")
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(v)
            return False

        return False

