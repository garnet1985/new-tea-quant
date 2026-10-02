"""价格层建议：先改想法再动资金；无对照格不编百分比。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

_SUGGESTIONS = {
    "empty_book": {
        "id": "empty_book",
        "needs_overlay": False,
        "text": "先看枚举有没有机会、合并是不是并光了。不要先改槽位。",
    },
    "has_edge": {
        "id": "has_edge",
        "needs_overlay": False,
        "text": "价格账有边。账户不好再去查组合层（含同股已持仓跳过），不要先改仓位来「创造」边。",
    },
    "no_edge": {
        "id": "no_edge",
        "needs_overlay": True,
        "text": "先改想法（信号或目标），不要先改资金。overlays 对照的是这本账的均收益 / 胜率 / 结实程度，不要讲成 PE 贡献了多少机会。",
    },
    "profit_concentrated": {
        "id": "profit_concentrated",
        "needs_overlay": True,
        "text": "边靠少数几笔。旋钮一动请看头部占比是不是还在，不要只看均收益转正。",
    },
    "profit_fragile": {
        "id": "profit_fragile",
        "needs_overlay": False,
        "text": "去掉头部就不赚钱，先当没有普遍边。不要用这格 ROI 去调仓位。",
    },
    "exit_mix": {
        "id": "exit_mix",
        "needs_overlay": True,
        "text": "改止损 / 止盈幅度必须 overlays。本格只说钱从哪种出场来，不编改完会多赚多少。",
    },
    "yearly_unstable": {
        "id": "yearly_unstable",
        "needs_overlay": False,
        "text": "年份已经变号，稳不稳走滚动 sw，不要和参数战役混表。",
    },
    "no_enum_contrast": {
        "id": "no_enum_contrast",
        "needs_overlay": False,
        "text": "补跑枚举后再看合并偏。没有对照不要假设并掉的更差。",
    },
    "merged_worse": {
        "id": "merged_worse",
        "needs_overlay": False,
        "text": "并掉的续命中更差，去噪在干活。枚举纸面盈亏不要拿来当普遍盈利。",
    },
    "merged_better": {
        "id": "merged_better",
        "needs_overlay": False,
        "text": "并掉的更好，账本可能偏保守。不要用锁仓解释缺席；缺席是同段被并或涨跌停。",
    },
    "denoising_neutral": {
        "id": "denoising_neutral",
        "needs_overlay": False,
        "text": "笔数即使和枚举一样，这一章也要留着：它回答的是去噪账赚不赚钱，不是找没找到。",
    },
    "tradability_skip": {
        "id": "tradability_skip",
        "needs_overlay": False,
        "text": "涨停买不进不是锁仓。可交易性偏了就写在这层，不要把它算进组合漏掉。",
    },
    "not_account_return": {
        "id": "not_account_return",
        "needs_overlay": False,
        "text": "不要把价格 ROI 说成账户收益。钱够不够用、同股能不能再买，留给组合层。",
    },
}


class PriceAdvise:
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
