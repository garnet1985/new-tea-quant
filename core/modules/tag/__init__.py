"""
Tag 系统：场景化标签计算与落库。

公开类型见包导出；架构与 API 见模块根目录 `README.md` 与 `docs/`。
"""

# 导出核心类和模块，方便用户导入
from core.modules.tag.core.base_tag_worker import BaseTagWorker
from core.modules.tag.core.tag_manager import TagManager
from core.modules.tag.core.enums import TagUpdateMode
from core.modules.tag.core.config import get_scenarios_root

__all__ = [
    'BaseTagWorker',
    'TagManager',
    'TagUpdateMode',
    'get_scenarios_root',
]
