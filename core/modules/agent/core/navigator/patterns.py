"""Navigator traps：仅正则规则；固定回复在 ``prompts/replies.md``。"""

from __future__ import annotations

import re

BRAND_LEAK_RE = re.compile(
    r"("
    r"new\s*trading\s*question|"
    r"new\s*trading\s*query|"
    r"new\s*tea\s*question|"
    r"新采摘|"
    r"采摘的茶|"
    r"茶叶|"
    r"茶饮|"
    r"春茶"
    r")",
    re.IGNORECASE,
)
IDENTITY_BRAND_RE = re.compile(
    r"(新茶|ntq|new\s*tea(?:\s*quant)?)",
    re.IGNORECASE,
)
IDENTITY_ASK_RE = re.compile(
    r"(是什么|什么意思|啥意思|缩写|全称|简介|介绍|特点|概述|干什么|做什么|谁)",
)
# 明确执行意图（硬门禁）。勿单独匹配「回测/扫描/归因」以免说明书问答误进 worker。
FORCE_WORK_RE = re.compile(
    r"("
    r"(建|写|改|测|跑|重跑|再跑).{0,20}(策略|回测|组合)|"
    r"(帮我|请|麻烦|顺便|然后).{0,16}(回测|扫描|归因|重跑|改|写|校验)|"
    r"(扫描|归因|滚动).{0,10}(一下|一遍|当前|机会|组合|策略)|"
    r"校验策略|"
    r"缓存|复查|结果不对|报告不对|不对帮我|不可能|没结果|没有机会|重跑|再跑|可行"
    r")",
    re.IGNORECASE,
)
ADVICE_TRAP_RE = re.compile(
    r"("
    r"什么策略.{0,12}(赚|挣)|"
    r"哪些策略.{0,12}(赚|挣)|"
    r"(能|会)?赚钱的策略|"
    r"推荐.{0,12}策略|"
    r"投资建议|"
    r"(该|应该)?买什么|"
    r"买什么股|"
    r"稳赚|"
    r"怎么赚钱|"
    r"哪(个|种)策略.{0,12}(赚|好|强)"
    r")",
    re.IGNORECASE,
)
FABRICATED_STRATEGY_RE = re.compile(
    r"(策略\s*[A-Z]|Strategy\s*[A-Z]|策略[甲乙丙丁])",
    re.IGNORECASE,
)
OUT_OF_SCOPE_WEB_RE = re.compile(
    r"("
    r"新闻|"
    r"暴乱|"
    r"美联储|"
    r"(今天|昨日|本周|最近).{0,16}(大盘|上证|指数).{0,16}(怎么|为何|为什么|走|跌|涨)|"
    r"投资潜力|"
    r"(热度|流行度?).{0,10}(高不高|还大|怎么样)|"
    r"网上.{0,8}(流行|热门|验证)|"
    r"互联网.{0,6}(搜|查)|"
    r"政策.{0,16}导致.{0,10}(上涨|涨)|"
    r"市场验证过的.{0,10}因子|"
    r"资产负债表.{0,20}估值|"
    r"(贵州茅台|宁德时代).{0,24}(新闻|关注点|报道)|"
    r"法国.{0,12}(暴乱|骚乱).{0,16}A\s*股|"
    r"实时(行情|资讯|新闻)"
    r")",
    re.IGNORECASE,
)


def is_product_identity_question(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw or not IDENTITY_BRAND_RE.search(raw):
        return False
    if IDENTITY_ASK_RE.search(raw):
        return True
    return len(raw) <= 24


def is_investment_advice_trap(text: str) -> bool:
    raw = str(text or "").strip()
    return bool(raw and ADVICE_TRAP_RE.search(raw))


def is_out_of_scope_web_question(text: str) -> bool:
    raw = str(text or "").strip()
    return bool(raw and OUT_OF_SCOPE_WEB_RE.search(raw))


def has_brand_leak(text: str) -> bool:
    return bool(BRAND_LEAK_RE.search(str(text or "")))


def force_worker(text: str) -> bool:
    return bool(FORCE_WORK_RE.search(str(text or "")))
