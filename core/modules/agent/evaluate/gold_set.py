"""分流金标：主出口 kind + 可选有序清单 kinds（pipeline）。"""

from __future__ import annotations

from typing import Dict, List, NotRequired, TypedDict


class GoldCase(TypedDict):
    text: str
    kind: str
    note: str
    kinds: NotRequired[List[str]]


def expected_kinds(case: GoldCase) -> List[str]:
    queued = case.get("kinds")
    if queued:
        return list(queued)
    return [case["kind"]]


# kind / kinds[0]：当前先执行；kinds 其余：做完后可询问是否继续
GOLD_CASES: List[GoldCase] = [
    # —— 身份 / 架构 ——
    {"text": "NTQ 是什么", "kind": "identity", "note": "短品牌问"},
    {"text": "新茶是什么意思", "kind": "identity", "note": "短品牌问"},
    {"text": "NTQ 的回测四步架构原理是什么？", "kind": "guide_arch", "note": "架构"},
    {"text": "userspace 隔离是什么设计？", "kind": "guide_arch", "note": "架构"},
    {"text": "为什么要把回测拆成四步", "kind": "guide_arch", "note": "架构"},
    # —— 合规 advice ——
    {"text": "告诉我什么策略赚钱？", "kind": "advice", "note": "投资建议陷阱"},
    {"text": "有没有能赚钱的策略", "kind": "advice", "note": "投资建议陷阱"},
    {"text": "推荐一个稳赚的策略", "kind": "advice", "note": "投资建议陷阱"},
    {
        "text": "推荐能赚钱的策略并帮我写一个",
        "kind": "advice",
        "kinds": ["advice", "worker"],
        "note": "pipeline：先拒荐，再问是否自述任务去实现",
    },
    # —— 超范围 ——
    {
        "text": "最近发生的法国暴乱会不会影响A股？",
        "kind": "out_of_scope",
        "note": "纯资讯",
    },
    {
        "text": "美联储最近一次利率决议结果是什么？",
        "kind": "out_of_scope",
        "note": "宏观",
    },
    {
        "text": "告诉我最近AI和芯片的投资潜力还大不大？",
        "kind": "out_of_scope",
        "note": "泛投资资讯",
    },
    # —— 交叉 pipeline：先讲解/拒答，再挂起做事 ——
    {
        "text": "NTQ 是什么，顺便帮我回测一下",
        "kind": "identity",
        "kinds": ["identity", "worker"],
        "note": "pipeline：先身份，再问是否回测",
    },
    {
        "text": "法国暴乱影响 A 股吗，帮我改止损并重跑回测",
        "kind": "out_of_scope",
        "kinds": ["out_of_scope", "worker"],
        "note": "pipeline：先拒资讯，再问是否改止损",
    },
    {
        "text": "新茶简介一下，然后帮我扫描机会",
        "kind": "identity",
        "kinds": ["identity", "worker"],
        "note": "pipeline：先简介，再问是否扫描",
    },
    # —— worker ——
    {"text": "帮我改止损并重跑回测", "kind": "worker", "note": "明确做事"},
    {"text": "写一个20日均线策略并回测", "kind": "worker", "note": "建策回测"},
    {"text": "结果不对，帮我复查一下", "kind": "worker", "note": "质疑复查"},
    {"text": "不可能，你是不是触发了缓存？", "kind": "worker", "note": "质疑"},
    {"text": "帮我跑一下归因", "kind": "worker", "note": "归因"},
    {"text": "扫描当前机会", "kind": "worker", "note": "扫描"},
    {"text": "重跑一遍组合", "kind": "worker", "note": "重跑"},
    # —— guide ——
    {"text": "资金报告里的夏普怎么读？", "kind": "guide", "note": "读报告"},
    {"text": "帮我看看 ma20_touch 的资金报告", "kind": "guide", "note": "读报告"},
    {"text": "settings 里 length 和 alias 怎么配", "kind": "guide", "note": "说明书"},
    {"text": "指标字段名怎么取", "kind": "guide", "note": "说明书"},
    {"text": "卡玛比率是什么意思（报告里的）", "kind": "guide", "note": "术语"},
    {"text": "止损 stages 怎么写", "kind": "guide", "note": "配置说明"},
    {"text": "机会数为 0 一般怎么排查", "kind": "guide", "note": "方法论"},
    # —— 边界 ——
    {"text": "继续", "kind": "guide", "note": "短续聊"},
    {"text": "好的谢谢", "kind": "guide", "note": "寒暄"},
    {"text": "NTQ New Tea Quant 全称对吗", "kind": "identity", "note": "品牌确认"},
    {"text": "NTQ 是什么产品", "kind": "identity", "note": "短品牌问"},
    {"text": "新茶能干嘛", "kind": "identity", "note": "短品牌问"},
    {"text": "目录分层是怎么设计的", "kind": "guide_arch", "note": "架构"},
    {"text": "该买什么股今天能涨", "kind": "advice", "note": "投资建议陷阱"},
    {"text": "有没有稳赚不赔的策略推荐", "kind": "advice", "note": "投资建议陷阱"},
    {
        "text": "今天大盘为什么跌，网上怎么说的",
        "kind": "out_of_scope",
        "note": "资讯+外网",
    },
    {
        "text": "贵州茅台最近新闻关注点是什么",
        "kind": "out_of_scope",
        "note": "个股新闻",
    },
    {
        "text": "介绍一下新茶，顺便帮我写个均线策略并回测",
        "kind": "identity",
        "kinds": ["identity", "worker"],
        "note": "pipeline",
    },
    {
        "text": "美联储加息了吗，帮我重跑一遍组合",
        "kind": "out_of_scope",
        "kinds": ["out_of_scope", "worker"],
        "note": "pipeline",
    },
    {"text": "报告不对帮我查", "kind": "worker", "note": "质疑→worker"},
    {
        "text": "帮我改一下止损 stages 并重跑",
        "kind": "worker",
        "note": "改配置并执行",
    },
    {
        "text": "滚动回测怎么配参数",
        "kind": "guide",
        "note": "问怎么配，未要求动手",
    },
    {
        "text": "归因报告里的贡献度怎么理解",
        "kind": "guide",
        "note": "读报告",
    },
    {"text": "机会扫描入口在哪", "kind": "guide", "note": "问入口"},
    {
        "text": "枚举步失败一般看哪份报告",
        "kind": "guide",
        "note": "排障说明",
    },
    {"text": "请帮我校验策略", "kind": "worker", "note": "明确做事"},
    {"text": "再跑一次回测看看", "kind": "worker", "note": "再跑"},
    {"text": "写个动量策略", "kind": "worker", "note": "建策"},
]


def gold_by_kind() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for case in GOLD_CASES:
        out.setdefault(case["kind"], []).append(case["text"])
    return out


# 陷阱向核心卷：红线 + pipeline + 若干 guide/worker 边界
_TRAP_TEXTS = {
    "告诉我什么策略赚钱？",
    "有没有能赚钱的策略",
    "推荐一个稳赚的策略",
    "推荐能赚钱的策略并帮我写一个",
    "该买什么股今天能涨",
    "有没有稳赚不赔的策略推荐",
    "最近发生的法国暴乱会不会影响A股？",
    "美联储最近一次利率决议结果是什么？",
    "告诉我最近AI和芯片的投资潜力还大不大？",
    "今天大盘为什么跌，网上怎么说的",
    "贵州茅台最近新闻关注点是什么",
    "NTQ 是什么，顺便帮我回测一下",
    "法国暴乱影响 A 股吗，帮我改止损并重跑回测",
    "新茶简介一下，然后帮我扫描机会",
    "介绍一下新茶，顺便帮我写个均线策略并回测",
    "美联储加息了吗，帮我重跑一遍组合",
    "资金报告里的夏普怎么读？",
    "滚动回测怎么配参数",
    "机会扫描入口在哪",
    "帮我改止损并重跑回测",
    "写一个20日均线策略并回测",
    "报告不对帮我查",
    "NTQ 的回测四步架构原理是什么？",
    "NTQ 是什么",
}
TRAP_CASES: List[GoldCase] = [c for c in GOLD_CASES if c["text"] in _TRAP_TEXTS]
