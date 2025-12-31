"""
Job Builder - Job 构建器模块

职责：
1. 构建 jobs（每个 entity 一个 job）
2. 决定多进程 worker 数量
3. 提供 job 相关的辅助方法
"""
from app.tag.core.components.job_builder.job_builder import JobBuilder

__all__ = ['JobBuilder']
