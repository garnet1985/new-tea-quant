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

# 诊断日志：每个子进程只输出一次，避免刷屏
_DIAG_PRINTED = False


class ExampleActivityHighStrategyWorker(BaseStrategyWorker):
    def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Opportunity]:
        core = settings.get("core", {}) or {}

        # 1) Tag gate：activity_high 必须为 True
        gate_tag_name = core.get("activity_gate_tag_name", "activity_high")
        # 调试：输出当前已加载的 tag 行数
        tags = data.get("tags", []) or []
        self._diag_once(data=data, gate_tag_name=gate_tag_name, tags=tags, settings=settings)

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

    def _diag_once(self, *, data: Dict[str, Any], gate_tag_name: str, tags: Any, settings: Dict[str, Any]) -> None:
        global _DIAG_PRINTED
        if _DIAG_PRINTED:
            return
        _DIAG_PRINTED = True

        try:
            klines = data.get("klines", []) or []
            today = klines[-1].get("date") if klines else None

            rsi_length = int(settings["data"]["indicators"]["rsi"][0].get("period"))
            rsi_field = f"rsi{rsi_length}"
            latest_rsi = klines[-1].get(rsi_field) if klines else None

            latest_gate_event = self._latest_tag_event(tags, gate_tag_name)

            msg = (
                "DIAG_TAG_GATE "
                f"stock={getattr(self, 'stock_id', None)} "
                f"today={today} "
                f"tags_rows={(len(tags) if isinstance(tags, list) else None)} "
                f"gate_tag={gate_tag_name} "
                f"latest_gate_event={latest_gate_event} "
                f"latest_rsi={latest_rsi} "
                f"rsi_thr={(settings.get('core', {}) or {}).get('rsi_oversold_threshold')}"
            )
            # 用 WARNING + print 确保在多进程/不同日志级别下也能看到
            logger.warning(msg)
            print(msg)
        except Exception as e:
            logger.warning("DIAG_TAG_GATE failed: %s", e)

    @staticmethod
    def _latest_tag_event(tag_rows: Any, tag_name: str) -> Optional[Dict[str, Any]]:
        if not tag_rows:
            return None
        if not isinstance(tag_rows, list):
            return {"type": str(type(tag_rows))}

        for row in reversed(tag_rows):
            if (row.get("tag_name") or row.get("name")) != tag_name:
                continue
            return {
                "as_of_date": row.get("as_of_date"),
                "json_value": row.get("json_value"),
                "entity_id": row.get("entity_id"),
            }
        return None

