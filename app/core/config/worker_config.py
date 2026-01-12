#!/usr/bin/env python3
"""
Worker Configuration - Worker 配置

⚠️ 核心配置，不建议用户修改！

说明：
- 定义各模块的任务类型和预留核心数
- 用于自动计算 max_workers
- 如果用户非要改，请确保理解每个配置的含义
"""

from app.core.infra.worker.multi_process.task_type import TaskType


# ========================================
# 模块任务配置（⚠️ 核心配置）
# ========================================
MODULE_TASK_CONFIG = {
    # OpportunityEnumerator: 机会枚举器
    # - 既有数据库查询（I/O），也有指标计算和止盈止损判断（CPU）
    # - 分类：混合型
    'OpportunityEnumerator': {
        'task_type': TaskType.MIXED,
        'reserve_cores': 2  # 预留 2 个核心给系统
    },
    
    # TagManager: 标签管理器
    # - 主要是数据库查询和写入（I/O）
    # - 分类：I/O 密集型
    'TagManager': {
        'task_type': TaskType.IO_INTENSIVE,
        'reserve_cores': 1  # I/O 密集型可以少预留
    },
    
    # Simulator: 策略模拟器
    # - 既有数据查询（I/O），也有止盈止损计算（CPU）
    # - 分类：混合型
    'Simulator': {
        'task_type': TaskType.MIXED,
        'reserve_cores': 2
    },
    
    # Scanner: 策略扫描器
    # - 主要是数据查询（I/O）和简单判断
    # - 分类：I/O 密集型
    'Scanner': {
        'task_type': TaskType.IO_INTENSIVE,
        'reserve_cores': 1
    },
    
    # DataSourceHandler: 数据源处理器
    # - 网络请求、数据库写入（I/O）
    # - 分类：I/O 密集型
    'DataSourceHandler': {
        'task_type': TaskType.IO_INTENSIVE,
        'reserve_cores': 1
    }
}


# ========================================
# 默认配置（未在上面配置的模块使用）
# ========================================
DEFAULT_TASK_CONFIG = {
    'task_type': TaskType.MIXED,
    'reserve_cores': 2
}


def get_module_config(module_name: str) -> dict:
    """
    获取模块的任务配置
    
    Args:
        module_name: 模块名称
    
    Returns:
        配置字典 {'task_type': TaskType, 'reserve_cores': int}
    """
    return MODULE_TASK_CONFIG.get(module_name, DEFAULT_TASK_CONFIG)
