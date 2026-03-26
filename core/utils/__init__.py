"""
Utils Package - 通用工具模块

提供各种通用工具类和服务：
- util: 配置合并工具
- date: 日期工具类
- icon: 图标服务
- progress: 进度条和跟踪器
"""
from .icon.icon_service import IconService, i as icon_i
try:
    from .utils import Utils
except ModuleNotFoundError as exc:
    # Allow lightweight imports (e.g. setup scripts only needing icon `i`)
    # before optional heavy dependencies such as pandas are installed.
    if exc.name != "pandas":
        raise
    Utils = None  # type: ignore[assignment]

try:
    from .date.date_utils import DateUtils
except ModuleNotFoundError as exc:
    if exc.name != "pandas":
        raise
    DateUtils = None  # type: ignore[assignment]

__all__ = [
    # 配置工具
    'Utils',
    'merge_mapping_configs',
    # 日期工具
    'DateUtils',
    # 图标服务
    'IconService',
    'i',  # 简化的图标获取函数：i("green_dot")
]

# 导出简化的图标函数（别名）
i = icon_i 