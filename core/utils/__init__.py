"""
Utils Package - 通用工具模块

提供各种通用工具类和服务：
- util: 配置合并工具
- date: 日期工具类
- icon: 图标服务
- progress: 进度条和跟踪器
"""
from .utils import Utils
from .date.date_utils import DateUtils
from .icon.icon_service import IconService, i as icon_i

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