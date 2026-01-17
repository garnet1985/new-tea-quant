"""
API Job Manager Service

API Job 管理 Service，负责初始化、缓存和管理 API Job 实例。
"""
from typing import Dict, Any, Optional, List
from loguru import logger

from core.modules.data_source.data_classes import ApiJob


class APIJobManager:
    """
    API Job Manager Service
    
    职责：
    - 从配置初始化 API Jobs
    - 缓存 API Job 实例
    - 提供获取和创建 API Job 的方法
    """
    
    def __init__(self):
        """初始化 Manager"""
        self._api_jobs: Dict[str, ApiJob] = {}  # API Job 实例缓存（name -> ApiJob 实例）
    
    def init_api_jobs(self, handler_config) -> None:
        """
        初始化 API Jobs（从 handler_config 中读取并创建 ApiJob 实例）
        
        从 handler_config.apis 读取字典格式的 API（name -> 配置），创建 ApiJob 实例并缓存。
        在初始化时进行配置验证，确保所有必需的字段都存在。
        
        Args:
            handler_config: HandlerConfig 对象（包含 apis 字典）
        
        Raises:
            ValueError: 如果配置无效（缺少 provider_name 或 method）
        """
        if not handler_config or not handler_config.apis:
            logger.debug(f"未配置任何 API")
            return
        
        for name, api_dict in handler_config.apis.items():
            if not isinstance(api_dict, dict):
                logger.warning(f"API '{name}' 配置格式错误（应为字典），跳过")
                continue
            
            # 验证必需字段
            provider_name = api_dict.get("provider_name")
            method = api_dict.get("method")
            
            if not provider_name:
                raise ValueError(
                    f"API '{name}' 配置缺少 'provider_name' 字段"
                )
            if not method:
                raise ValueError(
                    f"API '{name}' 配置缺少 'method' 字段"
                )
            
            # 创建 ApiJob 实例（使用配置中的默认 params，如果有的话）
            api_job = ApiJob(
                provider_name=provider_name,
                method=method,
                params=api_dict.get("params", {}) or {},  # 默认 params（可能为空）
                api_name=api_dict.get("api_name") or method,
                depends_on=api_dict.get("depends_on", []) or [],
                priority=api_dict.get("priority", 0),
                timeout=api_dict.get("timeout"),
                retry_count=api_dict.get("retry_count", 0),
            )
            
            self._api_jobs[name] = api_job
        
    
    def get_api_job(self, name: str) -> Optional[ApiJob]:
        """
        根据 name 获取缓存的 ApiJob 实例
        
        Args:
            name: API 名称（配置中的 key）
        
        Returns:
            ApiJob 实例，如果不存在则返回 None
        """
        return self._api_jobs.get(name)
    
    def get_api_job_with_params(
        self,
        name: str,
        params: Dict[str, Any],
        job_id: Optional[str] = None,
        **kwargs
    ) -> ApiJob:
        """
        获取 ApiJob 实例并设置新的 params（便捷方法）
        
        从缓存的 ApiJob 实例创建新实例，只修改 params 和其他指定字段。
        
        Args:
            name: API 名称（配置中的 key）
            params: API 调用参数（动态生成，会与配置中的默认 params 合并）
            job_id: Job ID（可选）
            **kwargs: 其他要修改的字段（depends_on, priority, timeout 等）
        
        Returns:
            ApiJob 对象（新实例）
        
        Raises:
            ValueError: 如果 API 不存在
        """
        from dataclasses import replace
        
        api_job_template = self.get_api_job(name)
        if not api_job_template:
            raise ValueError(
                f"API '{name}' 不存在。可用的 API: {list(self._api_jobs.keys())}"
            )
        
        # 合并默认 params 和传入的 params（传入的优先）
        default_params = api_job_template.params or {}
        final_params = {**default_params, **params}
        
        # 使用 replace 创建新实例，只修改指定字段
        return replace(
            api_job_template,
            params=final_params,
            job_id=job_id if job_id is not None else api_job_template.job_id,
            **kwargs
        )
    
    def list_api_names(self) -> List[str]:
        """
        列出所有已配置的 API 名称
        
        Returns:
            List[str]: API 名称列表
        """
        return list(self._api_jobs.keys())
