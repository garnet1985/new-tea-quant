from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from loguru import logger


class ProviderError(Exception):
    """Provider 统一错误类"""
    
    def __init__(self, provider: str, api: str, original_error: Exception):
        self.provider = provider
        self.api = api
        self.original_error = original_error
        super().__init__(f"[{provider}.{api}] {original_error}")


class BaseProvider(ABC):
    """
    第三方数据源提供者基类
    
    设计原则：
    1. 纯粹的 API 封装，不包含业务逻辑
    2. 声明式元数据（限流、认证）
    3. 简单、可测试
    
    子类必须定义：
    - provider_name: Provider 名称
    - requires_auth: 是否需要认证
    - auth_type: 认证类型
    - api_limits: API 限流信息（声明式）
    """
    
    # ========== 类属性（子类必须定义）==========
    provider_name: str = None              # Provider 名称，如 "tushare"
    requires_auth: bool = False            # 是否需要认证
    auth_type: Optional[str] = None        # 认证类型: "token" | "api_key" | None
    
    # API 限流信息（每分钟请求数）- 只声明，不执行
    # 例如：{"get_daily_kline": 100, "get_weekly_kline": 50}
    api_limits: Dict[str, int] = {}
    
    # 默认限流（如果 API 没有单独配置）
    default_rate_limit: Optional[int] = None
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 Provider
        
        Args:
            config: 配置信息（如 token, api_key 等）
        """
        self.config = config or {}
        self._validate_class_attributes()
        self._validate_config()
        self._initialize()
    
    def _validate_class_attributes(self):
        """验证子类是否定义了必需的类属性"""
        if self.provider_name is None:
            raise ValueError(f"{self.__class__.__name__} 必须定义 provider_name")
    
    def _validate_config(self):
        """验证配置（如 token 等）"""
        if self.requires_auth:
            if self.auth_type == "token" and not self.config.get("token"):
                raise ValueError(f"{self.provider_name} 需要 token")
            if self.auth_type == "api_key" and not self.config.get("api_key"):
                raise ValueError(f"{self.provider_name} 需要 api_key")
    
    @abstractmethod
    def _initialize(self):
        """
        初始化 Provider（如初始化 API 客户端）
        
        子类必须实现
        """
        pass
    
    # ========== 元信息获取 ==========
    
    def get_api_limit(self, api_name: str) -> Optional[int]:
        """
        获取指定 API 的限流信息（每分钟请求数）
        
        Args:
            api_name: API 方法名
            
        Returns:
            每分钟请求数限制，None 表示无限制
        """
        return self.api_limits.get(api_name, self.default_rate_limit)
    
    def get_metadata(self) -> Dict:
        """获取 Provider 元信息"""
        return {
            "provider_name": self.provider_name,
            "requires_auth": self.requires_auth,
            "auth_type": self.auth_type,
            "api_limits": self.api_limits,
            "default_rate_limit": self.default_rate_limit,
        }
    
    # ========== 错误处理 ==========
    
    def handle_error(self, error: Exception, api_name: str) -> ProviderError:
        """
        将第三方 API 错误转换为统一格式
        
        子类可以覆盖此方法来处理特定的错误类型
        
        Args:
            error: 原始错误
            api_name: API 方法名
            
        Returns:
            统一的 ProviderError
        """
        logger.error(f"{self.provider_name}.{api_name} 调用失败: {error}")
        return ProviderError(
            provider=self.provider_name,
            api=api_name,
            original_error=error
        )
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(provider={self.provider_name})>"

