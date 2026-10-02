"""把枚举事实收成基本结论。不编反事实百分比。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

_FEW_TOTAL = 10
_LOW_TRIGGER = 0.05
_TOP5_CONCENTRATED = 0.50
_CALENDAR_PEAK = 0.40
_SL_HEAVY = 0.40
_TP_HEAVY = 0.50
_EXPIRY_HEAVY = 0.40


class EnumerateConclude:
    """规则结论；一条 id 对应建议里的一条。"""

    @classmethod
    def run(cls, facts: Mapping[str, Any]) -> List[Dict[str, Any]]:
        quantity = dict(facts.get("quantity") or {})
        time_block = dict(facts.get("time") or {})
        exits = dict(facts.get("exits") or {})
        leftover = dict(facts.get("leftover_upside") or {})
        out: List[Dict[str, Any]] = []
        out.extend(cls._quantity(quantity))
        out.extend(cls._time(time_block, quantity))
        out.extend(cls._exits(exits))
        out.extend(cls._leftover(leftover))
        out.append(
            {
                "id": "gates_need_overlay",
                "text": (
                    "本格看不出各道门各自贡献了多少机会。"
                    "过滤贡献要 overlays 把该位置写成 None；"
                    "信号贡献要对照阈值。"
                ),
            }
        )
        return out

    @staticmethod
    def _quantity(quantity: Mapping[str, Any]) -> List[Dict[str, Any]]:
        total = int(quantity.get("total_opportunities") or 0)
        trigger = float(quantity.get("trigger_ratio") or 0.0)
        top5 = float(quantity.get("top5_share") or 0.0)
        out: List[Dict[str, Any]] = []
        if total < _FEW_TOTAL or trigger < _LOW_TRIGGER:
            out.append(
                {
                    "id": "few_opportunities",
                    "text": (
                        f"找到的机会偏少：共 {total} 笔，"
                        f"覆盖率 {trigger:.1%}。"
                    ),
                }
            )
        if total > 0 and top5 >= _TOP5_CONCENTRATED:
            out.append(
                {
                    "id": "stock_concentrated",
                    "text": (
                        f"机会集中在少数票：前 5 只占 {top5:.1%}。"
                    ),
                }
            )
        return out

    @staticmethod
    def _time(
        time_block: Mapping[str, Any], quantity: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        calendar = dict(time_block.get("calendar") or {})
        per_stock = dict(time_block.get("per_stock") or {})
        peak_share = float(calendar.get("peak_share") or 0.0)
        peak_month = str(calendar.get("peak_month") or "")
        conclusion = str(per_stock.get("dispersion_conclusion") or "")
        cv = float(per_stock.get("cv") or 0.0)
        out: List[Dict[str, Any]] = []
        if int(quantity.get("total_opportunities") or 0) > 0 and peak_share >= _CALENDAR_PEAK:
            out.append(
                {
                    "id": "calendar_clustered",
                    "text": (
                        f"日历扎堆：{peak_month or '峰值月'} 占触发量 {peak_share:.1%}。"
                        "这和每股间隔不是同一件事。"
                    ),
                }
            )
        if conclusion == "较集中" or cv >= 0.8:
            out.append(
                {
                    "id": "per_stock_clustered",
                    "text": (
                        f"同一只股票上的触发偏密：间隔 CV {cv:.2f}（{conclusion or '较集中'}）。"
                    ),
                }
            )
        return out

    @staticmethod
    def _exits(exits: Mapping[str, Any]) -> List[Dict[str, Any]]:
        completed = int(exits.get("completed_count") or 0)
        if completed <= 0:
            return []
        sl = float(exits.get("stop_loss_share") or 0.0)
        tp = float(exits.get("take_profit_share") or 0.0)
        expired = float(exits.get("expiration_share") or 0.0)
        out: List[Dict[str, Any]] = []
        if sl >= _SL_HEAVY:
            names = [
                str(item.get("entity_id") or "")
                for item in (exits.get("concentrated_stop_loss") or [])[:3]
                if item.get("entity_id")
            ]
            extra = f"主要在 { '、'.join(names) }。" if names else ""
            out.append(
                {
                    "id": "stop_loss_heavy",
                    "text": f"纸面路径止损偏多：占完成笔 {sl:.1%}。{extra}".rstrip(),
                }
            )
        if tp >= _TP_HEAVY:
            out.append(
                {
                    "id": "take_profit_heavy",
                    "text": f"纸面路径止盈偏多：占完成笔 {tp:.1%}。",
                }
            )
        if expired >= _EXPIRY_HEAVY:
            out.append(
                {
                    "id": "expiration_heavy",
                    "text": f"纸面路径过期偏多：占完成笔 {expired:.1%}。",
                }
            )
        return out

    @staticmethod
    def _leftover(leftover: Mapping[str, Any]) -> List[Dict[str, Any]]:
        if leftover.get("measurable"):
            return []
        mode = str(leftover.get("mode") or "")
        if mode in {"unknown", "no_take_profit"}:
            return []
        return [
            {
                "id": "leftover_not_measurable",
                "text": (
                    "当前止盈是一档全平，同一次回测看不到止盈后面还有没有涨。"
                    "禁止在这格结果上编「如果止盈更高会怎样」的百分比。"
                ),
            }
        ]
