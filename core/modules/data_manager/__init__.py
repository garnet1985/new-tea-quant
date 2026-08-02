"""
数据管理服务 - 统一的数据访问层（``modules.data_manager``）。

包根仅导出 ``DataManager``；``BaseTableNames`` 等类型见 ``contracts.py``。

使用方式::

    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=True)
    klines = data_mgr.stock.kline.load("000001.SZ", term="daily", adjust="qfq")
"""

from .data_manager import DataManager

__all__ = ["DataManager"]
