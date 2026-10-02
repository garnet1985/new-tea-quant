"""枚举层建议：有对照格才能量化；否则只给方向。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

_SUGGESTIONS = {
    "few_opportunities": {
        "id": "few_opportunities",
        "needs_overlay": True,
        "text": (
            "要验证是信号太严还是过滤在砍：overlays 放宽阈值，"
            "或把怀疑的过滤写成 None。本格没有对照，不编会多出多少笔。"
        ),
    },
    "stock_concentrated": {
        "id": "stock_concentrated",
        "needs_overlay": True,
        "text": (
            "放宽之后请同时看覆盖票数，不要只看机会总数——"
            "可能还是那几只票连打几枪。"
        ),
    },
    "calendar_clustered": {
        "id": "calendar_clustered",
        "needs_overlay": False,
        "text": "先分月看触发，再决定要不要加过滤压峰值月；不要和每股间隔混成一个分散度。",
    },
    "per_stock_clustered": {
        "id": "per_stock_clustered",
        "needs_overlay": False,
        "text": (
            "同一标的上偏密的机会，价格层会按间隔合并。"
            "枚举层保持全量，不要在这里做去重。"
        ),
    },
    "stop_loss_heavy": {
        "id": "stop_loss_heavy",
        "needs_overlay": True,
        "text": (
            "本格只能看到止损堆在哪些票、哪几个月。"
            "改止损幅度必须 overlays；不要用这格百分比当「收到会少亏多少」。"
        ),
    },
    "take_profit_heavy": {
        "id": "take_profit_heavy",
        "needs_overlay": True,
        "text": "止盈偏多不代表目标合理。要测后面还有没有涨，加分档或打开动态止盈，或对照全平 vs 分档。",
    },
    "expiration_heavy": {
        "id": "expiration_heavy",
        "needs_overlay": True,
        "text": "过期偏多时对照窗口天数；本格不编改窗口后的胜率。",
    },
    "leftover_not_measurable": {
        "id": "leftover_not_measurable",
        "needs_overlay": True,
        "text": "加分档（第一档不要 close_invest）或 actions 里 set_dynamic_loss，才能在同一次枚举里看到止盈后路径。",
    },
    "gates_need_overlay": {
        "id": "gates_need_overlay",
        "needs_overlay": True,
        "text": (
            "单次 version 落盘的都是各道门都过的。"
            "要回答「RSI 过滤的机会更多还是 PE 砍的更多」，写 overlays / matrix。"
        ),
    },
}


class EnumerateAdvise:
    """结论 id → 建议；没有对应结论就不写那条。"""

    @classmethod
    def run(
        cls,
        conclusions: Sequence[Mapping[str, Any]],
        facts: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        del facts
        out: List[Dict[str, Any]] = []
        seen = set()
        for item in conclusions:
            cid = str(item.get("id") or "").strip()
            if not cid or cid in seen:
                continue
            seen.add(cid)
            suggestion = _SUGGESTIONS.get(cid)
            if suggestion:
                out.append(dict(suggestion))
        return out
