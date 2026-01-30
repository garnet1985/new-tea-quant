"""
Entity：数据契约（schema + 表身份）

Entity 只定义「长什么样」和「对应哪张表」，不包含 renew/fetch。
Data Source 负责执行并产出符合 Entity schema 的数据、写入 Entity 对应的表。
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Entity:
    """实体数据契约：表名 + 字段约定（无 renew/fetch）"""

    name: str
    """实体类型名称，如 'Stock', 'KlineDaily'"""

    table_name: str
    """对应 DB 表名，如 'stock_list', 'kline_daily'"""

    schema: Dict[str, Any]
    """字段约定：字段名 -> 类型或配置（与 DataSourceSchema 对齐时可共用）"""

    unique_keys: Optional[List[str]] = None
    """写入时去重/替换用的键，如 ['id'], ['id', 'date']"""

    def get_unique_keys(self) -> List[str]:
        """返回唯一键列表，未配置时返回空列表"""
        return list(self.unique_keys) if self.unique_keys else []
