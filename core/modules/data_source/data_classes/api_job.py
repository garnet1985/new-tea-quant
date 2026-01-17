"""
API Job 定义

ApiJob: 单个 API 调用任务（最小执行单元）
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


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
