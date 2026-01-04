from app.core.modules.data_source.data_source_manager import DataSourceManager
from app.core.modules.data_source.base_handler import BaseHandler  # 旧版本，保留兼容
from app.core.modules.data_source.base_provider import BaseProvider
from app.core.modules.data_source.data_source_handler import BaseDataSourceHandler
from app.core.modules.data_source.api_job import ApiJob, DataSourceTask

__all__ = [
    'DataSourceManager',
    'BaseHandler',  # 旧版本
    'BaseProvider',
    'BaseDataSourceHandler',  # 新版本
    'ApiJob',
    'DataSourceTask',
]
