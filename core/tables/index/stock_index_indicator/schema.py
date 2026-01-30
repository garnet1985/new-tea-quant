"""
data_stock_index_indicator 表结构定义（Python，变量名 schema）

股指指标。主键、时序列 id/term/date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_stock_index_indicator",
    "primaryKey": ["id", "term", "date"],
    "fields": [
        {"name": "id", "type": "varchar", "length": 16, "isRequired": True, "nullable": False, "description": "股指代码"},
        {"name": "term", "type": "varchar", "length": 16, "isRequired": True, "nullable": False},
        {"name": "date", "type": "varchar", "length": 8, "isRequired": True, "nullable": False},
        {"name": "open", "type": "float", "isRequired": True, "nullable": True},
        {"name": "close", "type": "float", "isRequired": True, "nullable": True},
        {"name": "highest", "type": "float", "isRequired": True, "nullable": True},
        {"name": "lowest", "type": "float", "isRequired": True, "nullable": True},
        {"name": "price_change_delta", "type": "float", "isRequired": False, "nullable": True},
        {"name": "price_change_rate_delta", "type": "float", "isRequired": False, "nullable": True},
        {"name": "pre_close", "type": "float", "isRequired": False, "nullable": True},
        {"name": "volume", "type": "bigint", "isRequired": False, "nullable": True},
        {"name": "amount", "type": "float", "isRequired": False, "nullable": True},
    ],
    "indexes": [
        {"name": "idx_id_term_date", "fields": ["id", "term", "date"], "unique": True},
        {"name": "idx_id_date", "fields": ["id", "date"]},
        {"name": "idx_id_term", "fields": ["id", "term"]},
    ],
}
