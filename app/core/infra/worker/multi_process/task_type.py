#!/usr/bin/env python3
"""
Task Type - 任务类型枚举

用于多进程 worker 数量计算
"""

from enum import Enum


class TaskType(Enum):
    """任务类型枚举"""
    
    CPU_INTENSIVE = 'cpu_intensive'  # CPU 密集型（如大量计算）
    IO_INTENSIVE = 'io_intensive'    # I/O 密集型（如数据库查询、文件读写）
    MIXED = 'mixed'                  # 混合型（既有计算也有 I/O）
    
    def __str__(self):
        return self.value
