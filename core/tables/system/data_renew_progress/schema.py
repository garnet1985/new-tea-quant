"""
sys_meta_data_renew_progress：每个数据源、每个实体、每个周期已经成功更新到的数据日期。

- source 是 mapping.py 里的数据源名字，例如 stock_klines、cpi。
- entity_id 是股票、指数或行业代码。整张表一起更新的数据源用 _global。
- term 是周期，例如 daily、weekly、monthly。没有周期时写成空字符串，这样主键里没有 NULL。
- last_update_date 是数据日期（YYYYMMDD、YYYYMM 或 2025Q4），不是墙上的“今天”。
  只有这一段数据已经写进库，或者官网明确说这段已经读完，才允许改它，并且只往更晚的日期改。

没有某一行，表示这个实体还没更新过，下次从默认起点拉。
补记完成会写一行 source=__renew_progress__、entity_id=backfill，避免每次启动都再扫一遍业务表。
"""
schema = {
    "storage_domain": "data",
    "update_key": "system_data_renew_progress",
    "kind": "meta",
    "name": "sys_meta_data_renew_progress",
    "primaryKey": ["source", "entity_id", "term"],
    "fields": [
        {
            "name": "source",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": False,
            "description": "数据源名字，与 mapping.py 的 key 相同",
        },
        {
            "name": "entity_id",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": False,
            "description": "股票、指数或行业代码；整表数据源为 _global",
        },
        {
            "name": "term",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "周期。没有周期时为空字符串",
        },
        {
            "name": "last_update_date",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "这个实体这个周期已经成功更新到的数据日期",
        },
    ],
    "indexes": [
        {
            "name": "idx_source",
            "fields": ["source"],
            "description": "按数据源读取已经更新到的日期",
        },
    ],
}
