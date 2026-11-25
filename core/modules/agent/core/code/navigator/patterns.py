"""Navigator traps：仅正则规则；固定回复在 ``content/**/replies.md``。"""

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
    r"(建|写|改|测|跑|重跑|再跑).{0,20}(策略|回测|组合|标签|打标)|"
    r"(帮我|请|麻烦|顺便|然后).{0,16}(回测|扫描|归因|重跑|改|写|校验|打标|标签)|"
    r"(扫描|归因|滚动).{0,10}(一下|一遍|当前|机会|组合|策略)|"
    r"(创建|新建|计算|跑).{0,8}(标签|打标)|"
    r"校验策略|校验标签|"
    # 研究假说：验证市场说法 / 把某信号当机会看能否赚钱 → worker（出测试计划），≠ 荐股 advice
    r"(帮我|请|麻烦)?(验证|检验|证伪|回测验证).{0,8}(一下|下|看)?|"
    r"(验证|检验|证伪).{0,24}(是不是|是否|会不会|假说|说法|规律)|"
    r"(利用|用).{0,24}(跳空|缺口|金叉|死叉|因子|信号|形态).{0,24}(盈利|赚钱|回测|验证)|"
    r"(把|将).{0,12}(跳空|缺口|金叉|死叉|因子|信号).{0,16}(当|当作|作为).{0,8}机会|"
    r"缓存|复查|结果不对|报告不对|不对帮我|不可能|没结果|没有机会|重跑|再跑|可行"
    r")",
    re.IGNORECASE,
)
# 荐股红线：点名买卖个股 / 该买什么。策略思路（含「能赚钱的策略」）走 guide，不在此列。
ADVICE_TRAP_RE = re.compile(
    r"("
    r"投资建议|"
    r"荐股|"
    r"(该|应该)?买什么|"
    r"买什么股|"
    r"买哪(只|支|个)股|"
    r"哪(只|支)股.{0,12}(买|涨|赚)|"
    r"(今天|明日|明天).{0,8}(买|卖).{0,8}(什么|哪)|"
    r"(推荐|给我).{0,8}(几只|一只|一支).{0,6}股|"
    r"(看好|建议买).{0,12}(股|标的|代码)"
    r")",
    re.IGNORECASE,
)
# 策略思路：要类型/逻辑/推荐思路（可含盈利导向用语）→ guide；同意测试后再 worker。
STRATEGY_IDEAS_RE = re.compile(
    r"("
    r"什么策略.{0,12}(赚|挣)|"
    r"哪些策略.{0,12}(赚|挣)|"
    r"(能|会)?赚钱的策略|"
    r"推荐.{0,12}策略|"
    r"策略.{0,8}(思路|想法|灵感)|"
    r"(没|没有).{0,8}(策略)?.{0,8}(思路|想法)|"
    r"(给我|有没有).{0,8}(一些|几个)?.{0,8}(策略)?(思路|想法)|"
    r"稳赚.{0,8}策略|"
    r"哪(个|种)策略.{0,12}(赚|好|强)|"
    r"怎么.{0,6}(制定|设计|想).{0,6}策略"
    r")",
    re.IGNORECASE,
)
FABRICATED_STRATEGY_RE = re.compile(
    r"(策略\s*[A-Z]|Strategy\s*[A-Z]|策略[甲乙丙丁])",
    re.IGNORECASE,
)
# 仅拦「当行情终端」类；新闻/宏观/名词走 guide + web_search。荐股仍由 ADVICE_TRAP。
OUT_OF_SCOPE_WEB_RE = re.compile(
    r"("
    r"实时(行情|报价|股价|盘口|资讯)|"
    r"(现在|此刻|盘中).{0,12}(多少钱|什么价|股价|行情|报价)|"
    r"(最新|实时).{0,8}(股价|报价|tick|盘口)|"
    r"(查|看|给我).{0,6}(一下)?.{0,6}(实时|盘中).{0,8}(行情|报价)"
    r")",
    re.IGNORECASE,
)
# 可搜网的知识/资讯（进 guide，可与 worker 排队）
WEB_KNOWLEDGE_RE = re.compile(
    r"("
    r"新闻|"
    r"资讯|"
    r"暴乱|"
    r"美联储|"
    r"(今天|昨日|本周|最近|最新).{0,16}(资讯|新闻|热点|消息)|"
    r"(几条|三条|两条|一条).{0,8}(资讯|新闻)|"
    r"(今天|昨日|本周|最近).{0,16}(大盘|上证|指数).{0,16}(怎么|为何|为什么|走|跌|涨)|"
    r"投资潜力|"
    r"(热度|流行度?).{0,10}(高不高|还大|怎么样)|"
    r"网上.{0,8}(流行|热门|验证|怎么说)|"
    r"互联网.{0,6}(搜|查)|"
    r"政策.{0,16}导致.{0,10}(上涨|涨)|"
    r"(贵州茅台|宁德时代).{0,24}(新闻|关注点|报道)|"
    r"法国.{0,12}(暴乱|骚乱).{0,16}A\s*股|"
    r"加息了吗|"
    r"利率决议"
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
    """荐股 / 该买什么等红线；不含策略思路推荐。"""
    raw = str(text or "").strip()
    return bool(raw and ADVICE_TRAP_RE.search(raw))


def is_strategy_ideas_question(text: str) -> bool:
    """要策略类型/思路（可含赚钱用语）；应走 guide，先给思路再问是否测试。"""
    raw = str(text or "").strip()
    if not raw or is_investment_advice_trap(raw):
        return False
    return bool(STRATEGY_IDEAS_RE.search(raw))


def is_out_of_scope_web_question(text: str) -> bool:
    raw = str(text or "").strip()
    return bool(raw and OUT_OF_SCOPE_WEB_RE.search(raw))


def is_web_knowledge_question(text: str) -> bool:
    """新闻/宏观/事件背景等：应走 guide（可 web_search），不是 out_of_scope。"""
    raw = str(text or "").strip()
    if not raw or is_out_of_scope_web_question(raw):
        return False
    return bool(WEB_KNOWLEDGE_RE.search(raw))


def has_brand_leak(text: str) -> bool:
    return bool(BRAND_LEAK_RE.search(str(text or "")))


def force_worker(text: str) -> bool:
    return bool(FORCE_WORK_RE.search(str(text or "")))
