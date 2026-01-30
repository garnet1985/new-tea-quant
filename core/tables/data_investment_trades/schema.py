"""
data_investment_trades 表结构定义（Python，变量名 schema）

投资交易。主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_investment_trades",
    "primaryKey": "id",
    "fields": [
        {"name": "id", "type": "int", "isRequired": True, "nullable": False, "autoIncrement": True, "description": "交易ID"},
        {"name": "stock_id", "type": "varchar", "length": 16, "isRequired": True, "nullable": True, "description": "股票代码"},
        {"name": "strategy", "type": "varchar", "length": 64, "isRequired": False, "nullable": True, "description": "策略名称"},
        {"name": "goal_config", "type": "json", "isRequired": False, "nullable": True, "description": "策略goal配置快照"},
        {"name": "status", "type": "varchar", "length": 16, "isRequired": False, "nullable": True, "default": "open", "description": "状态 open/closed"},
        {"name": "note", "type": "text", "isRequired": False, "nullable": True, "description": "备注"},
        {"name": "created_at", "type": "timestamp", "isRequired": False, "nullable": True, "default": "CURRENT_TIMESTAMP"},
        {"name": "updated_at", "type": "timestamp", "isRequired": False, "nullable": True, "default": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"},
    ],
    "indexes": [
        {"name": "idx_stock_id", "fields": ["stock_id"]},
        {"name": "idx_status", "fields": ["status"]},
        {"name": "idx_created_at", "fields": ["created_at"]},
    ],
}
