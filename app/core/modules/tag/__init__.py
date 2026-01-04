"""
Tag 系统 - 标签计算和存储框架

Tag 系统是一个灵活的标签计算和存储框架，用于为实体（股票、指数等）计算和存储各种标签。
支持自定义计算逻辑和定期切片两种模式。

设计理念：
- 存储层极简：只负责存和查，不关心怎么算
- 计算层灵活：支持自定义 calculator，遍历历史数据
- 配置驱动：通过配置文件定义 tag 的计算逻辑
- 性能优先：支持增量计算、多线程/进程并行计算
"""

# 导出核心类和模块，方便用户导入
from app.core.modules.tag.core.base_tag_worker import BaseTagWorker
from app.core.modules.tag.core.tag_manager import TagManager
from app.core.modules.tag.core.enums import TagUpdateMode
from app.core.modules.tag.core.config import DEFAULT_SCENARIOS_ROOT

__all__ = [
    'BaseTagWorker',
    'TagManager',
    'TagUpdateMode',
    'DEFAULT_SCENARIOS_ROOT',
]
