from __future__ import annotations

from enum import Enum


class DataKey(str, Enum):
    """
    Core DataKey 白名单（框架内置；**业务侧勿改本文件**以免升级覆盖）。

    **语义**：对外依赖的主标识之一；与 userspace 自定义 key（同形字符串 + 注册）的关系见 `CONCEPTS.md`。

    **注意**：本枚举的「DataKey」是 **字符串 id**；目标架构里「DataKey + issue 句柄 + load」的完整说明不在此文件。
    """

    # =========================
    # Stock (per-entity time axis)
    # =========================
    STOCK_KLINE_DAILY_QFQ = "stock.kline.daily.qfq"
    STOCK_KLINE_DAILY_NFQ = "stock.kline.daily.nfq"

    STOCK_ADJ_FACTOR_EVENTS = "stock.adj_factor.eventlog"

    STOCK_CORPORATE_FINANCE = "stock.finance.quarterly"

    # =========================
    # Tag (polymorphic; kind decided by scenario/definition meta)
    # =========================
    TAG_SCENARIO = "tag.scenario"

    # =========================
    # Index
    # =========================
    INDEX_LIST = "index.list"
    INDEX_KLINE_DAILY = "index.kline.daily"
    INDEX_WEIGHT_DAILY = "index.weight.daily"

    # =========================
    # Macro (global time axis)
    # =========================
    MACRO_GDP = "macro.gdp"
    MACRO_LPR = "macro.lpr"
    MACRO_CPI = "macro.cpi"
    MACRO_PPI = "macro.ppi"
    MACRO_PMI = "macro.pmi"
    MACRO_SHIBOR = "macro.shibor"
    MACRO_MONEY_SUPPLY = "macro.money_supply"

    # =========================
    # Static category / dictionaries
    # =========================
    STOCK_LIST = "stock.list"

    STOCK_INDUSTRIES = "stock.industries"
    STOCK_BOARDS = "stock.boards"
    STOCK_MARKETS = "stock.markets"

    STOCK_INDUSTRY_MAP = "stock.industry_map"
    STOCK_BOARD_MAP = "stock.board_map"
    STOCK_MARKET_MAP = "stock.market_map"

    # =========================
    # System/meta
    # =========================
    SYSTEM_META_INFO = "system.meta_info"
    SYSTEM_CACHE = "system.cache"
