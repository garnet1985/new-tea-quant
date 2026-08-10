"""数据源模块 — 包根仅导出 ``DataSourceManager``；基类与 job 类型见 ``contracts.py``。"""

from core.modules.data_source.core.data_source_manager import DataSourceManager

DataSourceManager.ensure_calendar_real_world_fetcher_registered()

__all__ = ["DataSourceManager"]
