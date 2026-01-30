"""
data_investment_operations 表结构定义（Python，变量名 schema）

投资操作记录。主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_investment_operations",
    "primaryKey": "id",
    "fields": [
        {"name": "id", "type": "int", "isRequired": True, "nullable": False, "autoIncrement": True, "description": "操作ID"},
        {"name": "trade_id", "type": "int", "isRequired": True, "nullable": True, "description": "所属交易ID"},
        {"name": "type", "type": "varchar", "length": 16, "isRequired": True, "nullable": True, "description": "操作类型 buy/sell/add"},
        {"name": "date", "type": "date", "isRequired": True, "nullable": True, "description": "操作日期"},
        {"name": "price", "type": "decimal", "length": "10,2", "isRequired": True, "nullable": True, "description": "操作价格"},
        {"name": "amount", "type": "int", "isRequired": True, "nullable": True, "description": "操作数量（股）"},
        {"name": "note", "type": "varchar", "length": 255, "isRequired": False, "nullable": True, "description": "备注"},
        {"name": "is_first", "type": "tinyint", "length": 1, "isRequired": False, "nullable": True, "default": 0, "description": "是否首次买入"},
        {"name": "created_at", "type": "timestamp", "isRequired": False, "nullable": True, "default": "CURRENT_TIMESTAMP"},
        {"name": "updated_at", "type": "timestamp", "isRequired": False, "nullable": True, "default": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"},
    ],
    "indexes": [
        {"name": "idx_trade_id", "fields": ["trade_id"]},
        {"name": "idx_date", "fields": ["date"]},
        {"name": "idx_trade_date", "fields": ["trade_id", "date"]},
    ],
}
