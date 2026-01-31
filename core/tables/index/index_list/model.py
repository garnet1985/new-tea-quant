"""
指数列表（sys_index_list）表 Model。

表初始值见同目录 data.json。
"""
from typing import List, Dict, Any
from core.infra.db import DbBaseModel
from core.tables.index.index_list.schema import schema as _schema


class DataIndexListModel(DbBaseModel):
    """指数列表表 Model（表名 sys_index_list）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["id"])
