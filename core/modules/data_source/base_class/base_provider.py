from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import os

from loguru import logger

from core.infra.project_context import PathManager
from core.modules.data_source.data_class.error import ProviderError
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
            config: 配置信息（如 token, api_key 等）。如果为 None，则按约定自动加载。
        """
        self._validate_class_attributes()

        # 如果未显式传入配置，则尝试按约定自动加载（例如 token）
        if config is None:
            config = self._load_default_config()

        self.config = config or {}
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

    def _load_default_config(self) -> Dict[str, Any]:
        """
        加载 Provider 默认配置（主要是认证信息）。

        约定（先实现最常用的 token 模式）：
        - 如果 requires_auth=False，返回空配置；
        - 如果 requires_auth=True 且 auth_type == "token"：
          1. 对于 provider_name == "tushare"：
             - 优先从 userspace/data_source/providers/tushare/auth_token.txt 读取 token；
             - 否则从环境变量 TUSHARE_TOKEN 读取；
             - 如果仍然没有，抛出带有清晰指引的错误；
          2. 其他 provider：
             - 优先从 {PROVIDER_NAME}_TOKEN 环境变量读取（大写）；
             - 如果没有且 requires_auth=True，则抛出错误提示。
        """
        config: Dict[str, Any] = {}

        if not self.requires_auth:
            return config

        # 目前仅支持 token 模式的自动加载
        if self.auth_type == "token":
            provider = self.provider_name or ""

            # 特殊处理 tushare：保持与之前 config.py 相同的行为
            if provider == "tushare":
                auth_token_path = PathManager.data_source_provider("tushare") / "auth_token.txt"
                if auth_token_path.exists():
                    try:
                        token = auth_token_path.read_text(encoding="utf-8").strip()
                        if token:
                            config["token"] = token
                        else:
                            logger.warning("auth_token.txt exists but is empty")
                    except Exception as e:
                        logger.warning(f"Failed to load auth_token.txt for tushare: {e}")

                if "token" not in config:
                    token = os.getenv("TUSHARE_TOKEN")
                    if token:
                        config["token"] = token

                if "token" not in config:
                    provider_path = PathManager.data_source_provider("tushare")
                    raise ValueError(
                        "Tushare token not found. Please:\n"
                        f"  1. Create {provider_path}/auth_token.txt with your token (one line)\n"
                        "  2. Or set environment variable: TUSHARE_TOKEN=your_token"
                    )

                return config

            # 其他 provider 的通用规则：从 {PROVIDER_NAME}_TOKEN 环境变量读取
            env_name = f"{provider.upper()}_TOKEN" if provider else None
            if env_name:
                token = os.getenv(env_name)
                if token:
                    config["token"] = token

            if "token" not in config:
                raise ValueError(
                    f"{self.provider_name} 需要 token，"
                    f"请设置环境变量 {env_name}=your_token，"
                    f"或在自定义 Provider 子类中覆盖 _load_default_config() 提供其他加载方式"
                )

        # 其他 auth_type 的情况，暂时返回空配置，交由调用方显式传入
        return config
    
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

