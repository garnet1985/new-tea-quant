from __future__ import annotations

from enum import Enum


class DataKey(str, Enum):
    """
    Core DataKey whitelist（随框架发布；**用户勿改本文件**，升级会覆盖）。

    用户自定义依赖标识：在 userspace 使用稳定字符串 + `userspace.data_contract` 注册路由，
    由 `DataContractManager` 与下表合并后注入策略等模块。

    - Strategy / 上游声明 *what*（DataKey 或 userspace 字符串 id）
    - Framework 解析 raw 并按路由表选择 Contract（how）
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

