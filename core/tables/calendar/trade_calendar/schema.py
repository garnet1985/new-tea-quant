"""
A 股交易日历（sys_trade_calendar）。

全量自然日：每个 cal_date 一行，is_open 表示是否交易（0 休市 / 1 交易）。
沪深 A 股共用上交所日历，默认 market=SSE（与 Tushare trade_cal 一致）。

数据来源：Tushare trade_cal（建议仅同步 SSE）。
"""
schema = {
    "storage_domain": "data",  # 市场/宏观/股票主数据等（data 域）
    "update_key": "system_trade_calendar",
    "name": "sys_trade_calendar",
    "primaryKey": ["market", "cal_date"],
    "fields": [
        {
            "name": "market",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "default": "SSE",
            "description": "交易所 SSE=上交所（A 股统一交易日历）",
        },
        {
            "name": "cal_date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "日历日期 YYYYMMDD",
        },
        {
            "name": "is_open",
            "type": "tinyint",
            "isRequired": True,
            "nullable": False,
            "description": "是否交易 0=休市 1=交易",
        },
    ],
    "indexes": [
        {"name": "idx_market_open_date", "fields": ["market", "is_open", "cal_date"]},
    ],
}
