"""数据库配置 dataclass（merge 后的 dict 在 ``build_engine_meta`` 处解析）。"""
from core.infra.db.settings.common import BatchWriteSettings, parse_batch_write

__all__ = ["BatchWriteSettings", "parse_batch_write"]
