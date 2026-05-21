"""
股票列表（sys_stock_list）：证券主表，存 L/D/P 全量及 PIT 日期字段。

维度属性由定义表 + 映射表维护（stock_list renew 时写入）：
- 行业：sys_industries + sys_stock_industry_map
- 板块：sys_boards + sys_stock_board_map（Tushare market）
- 交易所：sys_markets + sys_stock_market_map（Tushare exchange）
- 地域：sys_areas + sys_stock_area_map（Tushare area）

时点回测：list_date、delist_date；list_status 为同步快照（L/D/P）。

主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "update_key": "stock_stock_list",
    "name": "sys_stock_list",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "TS 代码 ts_code（含后缀，如 000001.SZ）",
        },
        {
            "name": "name",
            "type": "varchar",
            "length": 255,
            "isRequired": True,
            "nullable": True,
            "description": "股票简称",
        },
        {
            "name": "list_status",
            "type": "varchar",
            "length": 1,
            "isRequired": True,
            "nullable": True,
            "description": "上市状态快照：L上市 D退市 P暂停上市",
        },
        {
            "name": "list_date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": True,
            "description": "上市日期 YYYYMMDD",
        },
        {
            "name": "delist_date",
            "type": "varchar",
            "length": 8,
            "isRequired": False,
            "nullable": True,
            "description": "退市日期 YYYYMMDD，未退市为空",
        },
        {
            "name": "last_update",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "description": "本行最后同步时间",
        },
    ],
    "indexes": [
        {"name": "idx_list_status", "fields": ["list_status"]},
        {"name": "idx_list_date", "fields": ["list_date"]},
        {"name": "idx_delist_date", "fields": ["delist_date"]},
        {"name": "idx_list_delist_date", "fields": ["list_date", "delist_date"]},
    ],
}
