"""
个股资金流向（sys_stock_moneyflow）：Tushare moneyflow，按股票+交易日存储。

来源：Tushare API moneyflow（doc 170），大/中/小/特大单买卖与净流入。
主键 id/date nullable=false；其余 nullable=true。
"""
schema = {
    "storage_domain": "data",
    "update_key": "stock_moneyflow",
    "name": "sys_stock_moneyflow",
    "primaryKey": ["id", "date"],
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码 ts_code",
        },
        {
            "name": "date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "交易日期 YYYYMMDD",
        },
        {
            "name": "buy_sm_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "小单买入金额（万元）",
        },
        {
            "name": "sell_sm_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "小单卖出金额（万元）",
        },
        {
            "name": "buy_md_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "中单买入金额（万元）",
        },
        {
            "name": "sell_md_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "中单卖出金额（万元）",
        },
        {
            "name": "buy_lg_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "大单买入金额（万元）",
        },
        {
            "name": "sell_lg_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "大单卖出金额（万元）",
        },
        {
            "name": "buy_elg_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "特大单买入金额（万元）",
        },
        {
            "name": "sell_elg_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "特大单卖出金额（万元）",
        },
        {
            "name": "net_mf_vol",
            "type": "int",
            "isRequired": True,
            "nullable": True,
            "description": "净流入量（手）",
        },
        {
            "name": "net_mf_amount",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "净流入额（万元）",
        },
    ],
    "indexes": [
        {"name": "idx_id_date", "fields": ["id", "date"], "unique": True},
        {"name": "idx_date", "fields": ["date"]},
    ],
}
