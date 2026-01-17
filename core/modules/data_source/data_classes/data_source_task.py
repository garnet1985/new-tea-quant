"""
DataSource Task 定义

DataSourceTask: 业务任务（包含多个 ApiJobs，代表一个完整的数据处理流程）
"""
from dataclasses import dataclass
from typing import List, Optional, Callable

from .api_job import ApiJob


@dataclass
class DataSourceTask:
    """
    DataSource Task 定义
    
    一个 Task 代表一个业务任务，包含多个 ApiJobs，代表一个完整的数据处理流程
    
    例如：
    - 获取复权因子 Task：包含 Tushare K 线 ApiJob + AKShare 前复权价格 ApiJob
    - 获取股票 K 线 Task：包含日线、周线、月线三个 ApiJobs
    """
    # ========== 任务信息（必需）==========
    task_id: str                 # Task ID（唯一标识）
    api_jobs: List[ApiJob]        # 包含的 ApiJobs 列表
    
    # ========== 可选配置 ==========
    description: Optional[str] = None  # Task 描述
    merge_callback: Optional[Callable] = None  # 合并回调函数（可选，用于合并 ApiJobs 的结果）
    
    def __post_init__(self):
        """初始化后处理"""
        # 为每个 ApiJob 生成 job_id（如果未提供）
        for i, api_job in enumerate(self.api_jobs):
            if api_job.job_id is None:
                api_job.job_id = f"{self.task_id}_job_{i}"
