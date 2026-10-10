"""
申万一级行业日线（sys_sw_industry_kline）。

只存一级行业，外加申万 A 指 801003.SI（对照，不在分类树里）。
成交量单位是万股，成交额和市值单位是万元。个股日线成交额是千元，不能直接相加。
"""
schema = {
    "storage_domain": "data",
    "update_key": "stock_sw_industry_kline",
    "name": "sys_sw_industry_kline",
    "primaryKey": ["id", "date"],
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "申万指数代码。一级行业或申万 A 指 801003.SI",
        },
        {
            "name": "date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "交易日 YYYYMMDD",
        },
        {"name": "open", "type": "float", "isRequired": False, "nullable": True, "description": "开盘点位"},
        {"name": "high", "type": "float", "isRequired": False, "nullable": True, "description": "最高点位"},
        {"name": "low", "type": "float", "isRequired": False, "nullable": True, "description": "最低点位"},
        {"name": "close", "type": "float", "isRequired": False, "nullable": True, "description": "收盘点位"},
        {
            "name": "price_change_delta",
            "type": "float",
            "isRequired": False,
            "nullable": True,
            "description": "涨跌点位",
        },
        {
            "name": "price_change_rate_delta",
            "type": "float",
            "isRequired": False,
            "nullable": True,
            "description": "涨跌幅。来源字段 pct_change",
        },
        {
            "name": "volume",
            "type": "float",
            "isRequired": False,
            "nullable": True,
            "description": "成交量，万股",
        },
        {
            "name": "amount",
            "type": "float",
            "isRequired": False,
            "nullable": True,
            "description": "成交额，万元",
        },
        {"name": "pe", "type": "float", "isRequired": False, "nullable": True, "description": "市盈率"},
        {"name": "pb", "type": "float", "isRequired": False, "nullable": True, "description": "市净率"},
        {
            "name": "float_mv",
            "type": "float",
            "isRequired": False,
            "nullable": True,
            "description": "流通市值，万元",
        },
        {
            "name": "total_mv",
            "type": "float",
            "isRequired": False,
            "nullable": True,
            "description": "总市值，万元",
        },
    ],
    "indexes": [
        {"name": "idx_id_date", "fields": ["id", "date"], "unique": True},
        {"name": "idx_date", "fields": ["date"]},
    ],
}
