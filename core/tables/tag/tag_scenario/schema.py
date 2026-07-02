"""
sys_tag_scenario 表结构定义（Python，变量名 schema）

业务场景。主键 id nullable=false；其余 nullable=true。

字段说明：
- key: 简洁唯一标识（类似 strategy.key），用于精确定位 scenario
- name: 路径名称（相对 tags 根的 POSIX 路径）
- attach_to_data_key: Tag attach 的数据源（DataKey，例如 stock.kline.daily）
"""
schema = {
    "storage_domain": "tag",  # 标签定义与取值（tag 域）
    "update_key": "tag_tag_scenario",
    "name": "sys_tag_scenario",
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
            "name": "key",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": False,
            "description": "简洁唯一标识（类似 strategy.key）",
        },
        {
            "name": "name",
            "type": "varchar",
            "length": 128,
            "isRequired": True,
            "nullable": True,
            "description": "路径名称（相对 tags 根的 POSIX 路径）",
        },
        {
            "name": "display_name",
            "type": "varchar",
            "length": 128,
            "isRequired": False,
            "nullable": True,
            "description": "业务场景显示名称",
        },
        {
            "name": "description",
            "type": "text",
            "isRequired": False,
            "nullable": True,
            "description": "业务场景描述",
        },
        {
            "name": "attach_to_data_key",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": False,
            "description": "Tag attach 的数据源（DataKey，例如 stock.kline.daily）",
        },
        {
            "name": "created_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "default": "CURRENT_TIMESTAMP",
            "description": "创建时间",
        },
        {
            "name": "updated_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "default": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            "description": "更新时间",
        },
    ],
    "indexes": [
        {"name": "uk_key", "fields": ["key"], "unique": True},
        {"name": "uk_name", "fields": ["name"], "unique": True},
    ],
}
