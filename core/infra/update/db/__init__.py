"""
升级用单步数据脚本包。

由 ``core.infra.db`` 迁移执行器通过 ``update_key`` / ``action_id`` 注册表调用；
本包只放脚本实现，不负责 diff / plan / 编排。
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
