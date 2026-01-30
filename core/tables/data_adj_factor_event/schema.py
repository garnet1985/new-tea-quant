"""
data_adj_factor_event 表结构定义（Python，变量名 schema）

复权因子事件表，只存储复权因子变化的日期（除权除息日）。
主键、时序列 id/event_date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_adj_factor_event",
    "primaryKey": ["id", "event_date"],
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码（含市场后缀）",
        },
        {
            "name": "event_date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "除权除息日期 YYYYMMDD",
        },
        {
            "name": "factor",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "Tushare复权因子 F(t)",
        },
        {
            "name": "qfq_diff",
            "type": "float",
            "isRequired": False,
            "nullable": True,
            "default": 0.0,
            "description": "与EastMoney前复权价格的固定差异",
        },
        {
            "name": "last_update",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "default": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            "description": "记录最后更新时间",
        },
    ],
    "indexes": [
        {"name": "idx_id_event_date", "fields": ["id", "event_date"], "unique": True},
        {"name": "idx_id", "fields": ["id"]},
        {"name": "idx_event_date", "fields": ["event_date"]},
    ],
}
