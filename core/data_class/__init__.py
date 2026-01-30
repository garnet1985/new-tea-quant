"""
core.data_class：全局数据契约（Entity 等）

Entity 只做数据类：schema + table_name + unique_keys，无 renew/fetch。
"""
from core.data_class.entity import Entity, TimeSerialEntity

__all__ = ["Entity", "TimeSerialEntity"]
