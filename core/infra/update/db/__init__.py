"""
升级用单步数据脚本包。

公开推荐：``Update.data_scripts``；本子包供内部 / 兼容导入。
"""

from core.infra.update.db.registry import (
    get_data_script,
    list_registered_scripts,
    register_data_script,
    run_data_script,
)

__all__ = [
    "register_data_script",
    "get_data_script",
    "list_registered_scripts",
    "run_data_script",
]
