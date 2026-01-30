"""
data_stock_indicators 表结构定义（Python，变量名 schema）

股票日度基本面指标（原 daily_basic：PE、PB、换手率、市值等），与 K 线表分离。
主键、时序列 id/date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_stock_indicators",
    "primaryKey": ["id", "date"],
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
            "name": "turnover_rate",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "换手率",
        },
        {
            "name": "free_turnover_rate",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "自由流通股比例",
        },
        {
            "name": "volume_ratio",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "量比",
        },
        {
            "name": "pe",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "市盈率",
        },
        {
            "name": "pe_ttm",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "市盈率TTM",
        },
        {
            "name": "pb",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "市净率",
        },
        {
            "name": "ps",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "市销率",
        },
        {
            "name": "ps_ttm",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "市销率TTM",
        },
        {
            "name": "dv_ratio",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "分红比例",
        },
        {
            "name": "dv_ttm",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "分红比例TTM",
        },
        {
            "name": "total_share",
            "type": "bigint",
            "isRequired": True,
            "nullable": True,
            "description": "总股本",
        },
        {
            "name": "float_share",
            "type": "bigint",
            "isRequired": True,
            "nullable": True,
            "description": "流通股本",
        },
        {
            "name": "free_share",
            "type": "bigint",
            "isRequired": True,
            "nullable": True,
            "description": "自由流通股本",
        },
        {
            "name": "total_market_value",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "总市值",
        },
        {
            "name": "circ_market_value",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "流通市值",
        },
    ],
    "indexes": [
        {"name": "idx_id_date", "fields": ["id", "date"], "unique": True},
        {"name": "idx_date", "fields": ["date"]},
    ],
}
