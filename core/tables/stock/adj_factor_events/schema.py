"""
data_adj_factor_event 表结构定义（Python，变量名 schema）

复权因子事件表：每股按除权日存一条事件链。
- factor + qfq_anchor/raw_anchor：append 模型（消费端动态 offset）
- last_update：renew 门控（非 last_event_date）
"""
schema = {
    "storage_domain": "data",
    "update_key": "stock_adj_factor_events",
    "name": "sys_adj_factor_events",
    "primaryKey": ["id", "event_date"],
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码（含市场后缀，如 000001.SZ）",
        },
        {
            "name": "event_date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "事件日期 YYYYMMDD（除权日或首根 K 线日）",
        },
        {
            "name": "factor",
            "type": "double",
            "isRequired": True,
            "nullable": False,
            "description": "Tushare 绝对复权因子 F(t)，用于前链校验与 F(段)/F(最新)",
        },
        {
            "name": "qfq_anchor",
            "type": "double",
            "isRequired": False,
            "nullable": True,
            "description": "事件日外部数据源前复权收盘价快照（append 后不变）",
        },
        {
            "name": "raw_anchor",
            "type": "double",
            "isRequired": False,
            "nullable": True,
            "description": "事件日未复权收盘价快照（append 后不变）",
        },
        {
            "name": "qfq_diff",
            "type": "double",
            "isRequired": False,
            "nullable": True,
            "default": 0.0,
            "description": "可选缓存：入库时 F(最新) 下的 delta；消费优先 anchor 动态计算",
        },
        {
            "name": "last_update",
            "type": "datetime",
            "isRequired": False,
            "nullable": True,
            "description": "该股上次完成复权检查时间（renew_if_over_days 门控）",
        },
    ],
    "indexes": [
        {"name": "idx_id_event_date", "fields": ["id", "event_date"], "unique": True},
        {"name": "idx_id", "fields": ["id"]},
        {"name": "idx_event_date", "fields": ["event_date"]},
        {"name": "idx_id_last_update", "fields": ["id", "last_update"]},
    ],
}
