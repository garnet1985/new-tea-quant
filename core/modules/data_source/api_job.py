"""
API Job 和 DataSource Task 定义

- ApiJob: 单个 API 调用任务（最小执行单元）
- DataSourceTask: 业务任务（包含多个 ApiJobs，代表一个完整的数据处理流程）
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable


@dataclass
class ApiJob:
    """
    API Job 定义（带 Schema）
    
    一个 ApiJob 代表一个 API 调用任务，包含执行所需的所有信息
    """
    # ========== 执行信息（必需）==========
    provider_name: str           # Provider 名称
    method: str                  # Provider 方法名
    params: Dict[str, Any]       # 调用参数（已计算好）
    
    # ========== 依赖关系（可选）==========
    depends_on: List[str] = field(default_factory=list)  # 依赖的 ApiJob ID 列表（用于决定执行顺序）
    
    # ========== 元信息（可选，用于框架决策）==========
    job_id: Optional[str] = None  # Job ID（用于依赖关系，自动生成）
    api_name: Optional[str] = None  # API 名称（用于限流，默认 = method）
    
    # ========== 可选配置 ==========
    priority: int = 0            # 优先级（数字越大越优先）
    timeout: Optional[float] = None  # 超时时间（秒）
    retry_count: int = 0         # 重试次数
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果未指定 api_name，使用 method
        if self.api_name is None:
            self.api_name = self.method


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

