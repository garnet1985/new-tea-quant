"""数据源模块 — 包根仅导出 ``DataSourceManager``；基类与 job 类型见 ``contracts.py``。"""

from .data_source_manager import DataSourceManager

__all__ = ["DataSourceManager"]
