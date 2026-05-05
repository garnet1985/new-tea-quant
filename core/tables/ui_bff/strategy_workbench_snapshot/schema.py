"""
策略工作台快照版本表（sys_strategy_workbench_snapshot）。

一条记录对应某策略的一个用户可见版本（v1/v2/...）。
"""

schema = {
    "name": "sys_strategy_workbench_snapshot",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "bigint",
            "isRequired": True,
            "nullable": False,
            "autoIncrement": True,
            "description": "自增主键",
        },
        {
            "name": "strategy_name",
            "type": "varchar",
            "length": 128,
            "isRequired": True,
            "nullable": False,
            "description": "策略目录名",
        },
        {
            "name": "version",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "description": "策略内自增版本号（UI 显示 v{version}）",
        },
        {
            "name": "settings_snapshot",
            "type": "json",
            "isRequired": True,
            "nullable": False,
            "description": "该版本对应的完整 settings 快照",
        },
        {
            "name": "result_summary",
            "type": "json",
            "isRequired": False,
            "nullable": True,
            "description": "三个回测步骤的结果聚合：enum/price/capital",
        },
        {
            "name": "settings_finger_print_id",
            "type": "varchar",
            "length": 128,
            "isRequired": False,
            "nullable": True,
            "description": "settings 指纹",
        },
        {
            "name": "env_fingerprint_id",
            "type": "varchar",
            "length": 128,
            "isRequired": False,
            "nullable": True,
            "description": "环境指纹",
        },
        {
            "name": "created_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "description": "创建时间",
        },
        {
            "name": "updated_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "description": "最后更新时间（用于热度排序/清理）",
        },
    ],
    "indexes": [
        {"name": "uk_swb_snapshot_strategy_version", "fields": ["strategy_name", "version"], "unique": True},
        {"name": "idx_swb_snapshot_strategy_updated", "fields": ["strategy_name", "updated_at"]},
        {"name": "idx_swb_snapshot_strategy_settings_fp", "fields": ["strategy_name", "settings_finger_print_id"]},
        {"name": "idx_swb_snapshot_strategy_env_fp", "fields": ["strategy_name", "env_fingerprint_id"]},
    ],
}
