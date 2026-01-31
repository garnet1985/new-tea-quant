"""
data_stock_kline_daily 表结构定义（Python，变量名 schema）

仅 K 线价格与成交量字段，不含 term、不含 daily_basic 指标。
主键、时序列 id/date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_stock_klines",
    "primaryKey": ["id", "term", "date"],
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码ts_code",
        },
        {
            "name": "date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "交易日期",
        },
        {
            "name": "term",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": True,
            "description": "K线周期",
        },
        {
            "name": "open",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "开盘价",
        },
        {
            "name": "close",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "收盘价",
        },
        {
            "name": "highest",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "最高价",
        },
        {
            "name": "lowest",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "最低价",
        },
        {
            "name": "price_change_delta",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "涨跌额",
        },
        {
            "name": "price_change_rate_delta",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "涨跌幅",
        },
        {
            "name": "pre_close",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "昨收价",
        },
        {
            "name": "volume",
            "type": "bigint",
            "isRequired": True,
            "nullable": True,
            "description": "成交量",
        },
        {
            "name": "amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "成交额",
        },
    ],
    "indexes": [
        {"name": "idx_id_term_date", "fields": ["id", "term", "date"], "unique": True},
        {"name": "idx_id_term", "fields": ["id", "term"]},
        {"name": "idx_date", "fields": ["date"]},
    ],
}
