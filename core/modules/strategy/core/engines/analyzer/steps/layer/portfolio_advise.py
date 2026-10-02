"""组合层建议：先看买到 / 漏掉，再动资金；无对照格不编百分比。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

_SUGGESTIONS = {
    "no_price_contrast": {
        "id": "no_price_contrast",
        "needs_overlay": False,
        "text": "补跑价格层后再看买到 / 漏掉。没有账本不要假设槽位在挡好机会。",
    },
    "empty_book": {
        "id": "empty_book",
        "needs_overlay": False,
        "text": "先看价格账为什么是空的。不要先加槽。",
    },
    "no_buys": {
        "id": "no_buys",
        "needs_overlay": True,
        "text": "账户没成交。先查现金、槽位、同股已持仓，不要先改信号。无对照格不编改完会成交多少。",
    },
    "all_taken": {
        "id": "all_taken",
        "needs_overlay": False,
        "text": "价格账都买到了。账户不好先回价格层看边，不要先加槽。",
    },
    "fill_gap": {
        "id": "fill_gap",
        "needs_overlay": False,
        "text": "漏掉里含槽位满、现金不足、权重上限和同股已持仓。不要给每笔编跳过原因。",
    },
    "leftover_better": {
        "id": "leftover_better",
        "needs_overlay": True,
        "text": "漏掉更好，考虑加槽、改排序或放开同股。overlays 对照买到/漏掉质量差，不要编年化会高多少。",
    },
    "leftover_worse": {
        "id": "leftover_worse",
        "needs_overlay": False,
        "text": "漏掉更差，约束碰巧在过滤。不要为了成交率去加槽。",
    },
    "leftover_similar": {
        "id": "leftover_similar",
        "needs_overlay": True,
        "text": "漏掉和买到差不多。要论证加槽更赚，必须 overlays 真跑过组合格子。",
    },
    "slots_at_cap": {
        "id": "slots_at_cap",
        "needs_overlay": True,
        "text": "槽位顶满。加 max_portfolio_size 必须 overlays；没有格子只给方向，不编多赚几个点。",
    },
    "cash_idle": {
        "id": "cash_idle",
        "needs_overlay": True,
        "text": "平时现金闲、扎堆日才满。改等权 / Kelly / 单票上限必须对照格。",
    },
    "grouping_mismatch": {
        "id": "grouping_mismatch",
        "needs_overlay": True,
        "text": "钱没流向等权更赚的组。按因子排序再填槽要先改分配规则再跑；现有模式没有这一项就不要假装回测过。",
    },
    "profit_concentrated": {
        "id": "profit_concentrated",
        "needs_overlay": True,
        "text": "账户利润靠少数票。旋钮一动请看头部占比是不是还在，不要只看账户收益转正。",
    },
    "drawdown_crowded": {
        "id": "drawdown_crowded",
        "needs_overlay": True,
        "text": "回撤段槽位挤在一起。要验证分散，对照格看回撤段同时持仓，不要口头说换 Kelly 会更稳。",
    },
    "not_price_edge": {
        "id": "not_price_edge",
        "needs_overlay": False,
        "text": "不要把账户收益说成单笔等权边。边在不在是价格层的事。",
    },
}


class PortfolioAdvise:
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
