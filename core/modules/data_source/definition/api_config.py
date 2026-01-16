"""
API 配置定义

- ApiConfig: 单个 API 的配置
- ProviderConfig: 多个 API 的容器
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ApiConfig:
    """
    单个 API 的配置
    
    每个 API job 有自己的配置，包括：
    - Provider 信息
    - API 方法
    - 字段映射（可选，只有贡献字段到 Schema 的 API job 才需要）
    - API 特定参数
    - 依赖关系
    """
    provider_name: str  # Provider 名称（如 "tushare"）
    method: str  # API 方法名（如 "get_daily_kline"）
    api_name: Optional[str] = None  # API 名称（用于限流，默认等于 method）
    
    # 字段映射：该 API 的字段 → Schema 字段（可选）
    # 只有贡献字段到 Schema 的 API job 才需要配置
    field_mapping: Optional[Dict[str, str]] = None
    # 格式：{schema_field: api_field}
    # 例如：{"id": "ts_code", "date": "trade_date", "open": "open"}
    # 如果为 None，表示该 API job 不贡献字段到 Schema（可能是依赖）
    
    # API 特定参数（该 API 调用时使用的参数）
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 依赖关系（该 API job 依赖的其他 API job）
    depends_on: List[str] = field(default_factory=list)
    # 格式：["job_id_1", "job_id_2"]
    # 用于决定执行顺序（框架会自动进行拓扑排序）
    
    # Job ID（用于依赖关系，如果不指定会自动生成）
    job_id: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果未指定 api_name，使用 method
        if self.api_name is None:
            self.api_name = self.method


@dataclass
class ProviderConfig:
    """
    Provider 配置（支持多个 API）
    
    一个 Data Source 可以配置多个 API，每个 API 有自己的配置
    有些 API 贡献字段到 Schema（需要 field_mapping）
    有些 API 只是作为依赖（不需要 field_mapping）
    """
    apis: List[ApiConfig] = field(default_factory=list)
    
    # 便捷方法：单个 API 的情况
    @classmethod
    def single_api(
        cls,
        provider_name: str,
        method: str,
        field_mapping: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        api_name: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> "ProviderConfig":
        """
        创建单个 API 的 ProviderConfig（便捷方法）
        
        Args:
            provider_name: Provider 名称
            method: API 方法名
            field_mapping: 字段映射（可选）
            params: API 参数（可选）
            depends_on: 依赖列表（可选）
            api_name: API 名称（可选，默认等于 method）
            job_id: Job ID（可选）
        
        Returns:
            ProviderConfig 实例
        """
        api_config = ApiConfig(
            provider_name=provider_name,
            method=method,
            field_mapping=field_mapping,
            params=params or {},
            depends_on=depends_on or [],
            api_name=api_name,
            job_id=job_id,
        )
        return cls(apis=[api_config])
    
    def get_api_by_job_id(self, job_id: str) -> Optional[ApiConfig]:
        """根据 job_id 获取 ApiConfig"""
        for api in self.apis:
            if api.job_id == job_id:
                return api
        return None
    
    def get_apis_with_field_mapping(self) -> List[ApiConfig]:
        """获取所有有 field_mapping 的 API（贡献字段的 API）"""
        return [api for api in self.apis if api.field_mapping is not None]
