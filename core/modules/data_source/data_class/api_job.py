from typing import Any, Dict, List, Optional


class ApiJob:
    """
    轻量级的 Api Job 定义（供新 BaseHandler 管线使用）

    设计目标：
    - 显式构造：通过 __init__ 一次性传入所有字段，便于阅读和对比；
    - 字段全部可选，方便按需扩展；
    - 不在这里承载复杂逻辑，主要作为数据载体。
    """

    def __init__(
        self,
        api_name: Optional[str] = None,
        provider_name: Optional[str] = None,
        method: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        api_params: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        rate_limit: int = 0,
        job_id: Optional[str] = None,
    ):
        # 基本标识
        self.api_name: Optional[str] = api_name or method
        self.job_id: Optional[str] = job_id or self.api_name

        # Provider & 方法
        self.provider_name: Optional[str] = provider_name
        self.method: Optional[str] = method

        # 调用参数 & 原始配置
        self.params: Dict[str, Any] = params or {}
        self.api_params: Dict[str, Any] = api_params or {}

        # 依赖与限流
        self.depends_on: List[str] = depends_on or []
        self.rate_limit: int = rate_limit or 0

    def execute(self):
        """
        占位方法：具体执行由 Task/Executor 负责，这里不实现。
        """
        raise NotImplementedError("ApiJob.execute 由上层执行器负责，不应直接调用")