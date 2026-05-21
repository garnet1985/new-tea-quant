"""
股票风险警示时段表（sys_stock_st_periods）。

每行表示某只股票在某段简称下处于 ST / *ST 等状态的有效区间（PIT）。
主键 (stock_id, st_level, start_date)；end_date 为空表示仍有效。

数据来源以 Tushare namechange 的 name + start_date/end_date 为主。
"""
schema = {
    "update_key": "stock_stock_st_periods",
    "name": "sys_stock_st_periods",
    "primaryKey": ["stock_id", "st_level", "start_date"],
    "fields": [
        {
            "name": "stock_id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "TS 代码 ts_code",
        },
        {
            "name": "st_level",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "STAR_ST(*ST) / ST / SST / S_STAR_ST 等",
        },
        {
            "name": "start_date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "警示简称生效起点 YYYYMMDD",
        },
        {
            "name": "end_date",
            "type": "varchar",
            "length": 8,
            "isRequired": False,
            "nullable": True,
            "description": "警示简称生效终点（含当日）；空=仍有效",
        },
        {
            "name": "name_snapshot",
            "type": "varchar",
            "length": 64,
            "isRequired": False,
            "nullable": True,
            "description": "该时段证券简称快照",
        },
        {
            "name": "change_reason",
            "type": "varchar",
            "length": 255,
            "isRequired": False,
            "nullable": True,
            "description": "namechange.change_reason",
        },
        {
            "name": "ann_date",
            "type": "varchar",
            "length": 8,
            "isRequired": False,
            "nullable": True,
            "description": "公告日（元数据，不参与默认交易生效判断）",
        },
        {
            "name": "source",
            "type": "varchar",
            "length": 32,
            "isRequired": True,
            "nullable": True,
            "default": "namechange",
            "description": "数据来源",
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
        {"name": "idx_stock_id", "fields": ["stock_id"]},
        {"name": "idx_start_end", "fields": ["start_date", "end_date"]},
    ],
}
