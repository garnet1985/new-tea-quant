"""
DataSource Definition 核心类

标准化的 DataSource 配置对象，用于统一管理 DataSource 的配置。
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Type
from loguru import logger
import importlib

from .api_config import ApiConfig, ProviderConfig
from .handler_config import BaseHandlerConfig


@dataclass
class DataSourceDefinition:
    """
    DataSource 定义对象
    
    标准化的 DataSource 配置，包含：
    - Schema 关联（schema_name 总是等于 name）
    - Handler 配置
    - Provider 配置（支持多个 API）
    - 依赖关系
    - 其他可选配置
    """
    name: str  # DataSource 名称
    handler_path: str  # Handler 类的完整路径
    description: str = ""  # 描述
    
    @property
    def schema_name(self) -> str:
        """
        Schema 名称（总是等于 name）
        
        一个 DataSource 一定对应一个 Schema（1:1 关系）
        """
        return self.name
    
    handler_config: Optional[BaseHandlerConfig] = None  # Handler 特定配置
    
    provider_config: ProviderConfig = field(default_factory=ProviderConfig)  # Provider 配置
    
    dependencies: Dict[str, bool] = field(default_factory=dict)  # 全局依赖声明
    
    # 其他可选配置（未来扩展）
    # date_range: Optional[DateRangeConfig] = None
    # database: Optional[DatabaseConfig] = None
    # execution: Optional[ExecutionConfig] = None
    
    def validate(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            bool: 是否有效
        """
        # 验证必需字段
        if not self.name:
            logger.error("DataSourceDefinition.name 不能为空")
            return False
        
        if not self.handler_path:
            logger.error("DataSourceDefinition.handler_path 不能为空")
            return False
        
        # 验证 ProviderConfig
        if not self.provider_config.apis:
            logger.warning(f"DataSourceDefinition {self.name} 没有配置任何 API")
        
        # 验证每个 ApiConfig
        for api in self.provider_config.apis:
            if not api.provider_name:
                logger.error(f"ApiConfig.provider_name 不能为空 (job_id: {api.job_id})")
                return False
            if not api.method:
                logger.error(f"ApiConfig.method 不能为空 (job_id: {api.job_id})")
                return False
        
        # 验证依赖关系
        job_ids = {api.job_id for api in self.provider_config.apis if api.job_id}
        for api in self.provider_config.apis:
            for dep_job_id in api.depends_on:
                if dep_job_id not in job_ids:
                    logger.warning(
                        f"ApiConfig {api.job_id} 依赖的 job_id {dep_job_id} 不存在"
                    )
        
        return True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], name: Optional[str] = None) -> "DataSourceDefinition":
        """
        从字典创建 DataSourceDefinition
        
        配置格式：
        {
            "handler": "handlers.rolling.RollingHandler",
            "description": "...",
            "dependencies": {...},
            "provider_config": {
                "apis": [
                    {
                        "provider_name": "tushare",
                        "method": "get_gdp",
                        "field_mapping": {...},
                        "params": {...},
                        "depends_on": [...],
                        "api_name": "...",
                        "job_id": "..."
                    }
                ]
            },
            "handler_config": {
                "date_format": "quarter",
                "rolling_periods": 4,
                ...
            }
        }
        
        Args:
            data: 配置字典
            name: DataSource 名称（如果 data 中没有）
        
        Returns:
            DataSourceDefinition 实例
        """
        # 获取 name
        ds_name = name or data.get("name", "")
        if not ds_name:
            raise ValueError("DataSourceDefinition.name 不能为空")
        
        # 获取 handler_path
        handler_path = data.get("handler", "")
        if not handler_path:
            raise ValueError("DataSourceDefinition.handler_path 不能为空")
        
        # 获取 description
        description = data.get("description", "")
        
        # 获取 dependencies
        dependencies = data.get("dependencies", {})
        
        # 解析 ProviderConfig
        provider_config = cls._parse_provider_config(data)
        
        # 解析 HandlerConfig
        handler_config = cls._parse_handler_config(data, handler_path)
        
        # 创建实例
        definition = cls(
            name=ds_name,
            handler_path=handler_path,
            description=description,
            handler_config=handler_config,
            provider_config=provider_config,
            dependencies=dependencies,
        )
        
        # 验证
        if not definition.validate():
            logger.warning(f"DataSourceDefinition {ds_name} 验证失败，但继续创建")
        
        return definition
    
    @classmethod
    def _parse_provider_config(cls, data: Dict[str, Any]) -> ProviderConfig:
        """
        解析 ProviderConfig
        
        Args:
            data: 配置字典
        
        Returns:
            ProviderConfig 实例
        """
        provider_data = data.get("provider_config", {})
        apis = []
        
        for api_data in provider_data.get("apis", []):
            apis.append(ApiConfig(**api_data))
        
        return ProviderConfig(apis=apis)
    
    @classmethod
    def _parse_handler_config(
        cls, data: Dict[str, Any], handler_path: str
    ) -> Optional[BaseHandlerConfig]:
        """
        解析 HandlerConfig（自动发现机制）
        
        自动发现策略（按优先级）：
        1. 从 handler 类获取 config_class 类属性（推荐方式）
        2. 从 handler 模块导入 Config 类（约定命名：HandlerClassName + "Config"）
        3. 如果都找不到，返回 None（使用 BaseHandlerConfig 的默认行为）
        
        Args:
            data: 配置字典
            handler_path: Handler 路径（如 "userspace.data_source.handlers.kline.KlineHandler"）
        
        Returns:
            HandlerConfig 实例（如果找到对应的 Config 类），否则返回 None
        """
        try:
            # 解析 handler_path 获取模块路径和类名
            module_path, handler_class_name = handler_path.rsplit('.', 1)
            handler_module = importlib.import_module(module_path)
            handler_class = getattr(handler_module, handler_class_name, None)
            
            if not handler_class:
                logger.warning(f"无法找到 Handler 类 {handler_path}")
                return None
            
            config_class = None
            
            # 策略 1: 从 handler 类获取 config_class 类属性（推荐）
            if hasattr(handler_class, 'config_class'):
                config_class = handler_class.config_class
                if config_class and issubclass(config_class, BaseHandlerConfig):
                    # 找到 Config 类，使用它
                    handler_config_data = data.get("handler_config", {})
                    try:
                        return config_class(**handler_config_data)
                    except Exception as e:
                        logger.warning(f"创建 HandlerConfig 失败 {handler_path}: {e}，使用默认配置")
                        return config_class()
            
            # 策略 2: 从 handler 模块导入 Config 类（约定命名：HandlerClassName + "Config"）
            # 例如：KlineHandler -> KlineHandlerConfig
            config_class_name = handler_class_name + "Config"
            config_class = getattr(handler_module, config_class_name, None)
            if config_class and issubclass(config_class, BaseHandlerConfig):
                handler_config_data = data.get("handler_config", {})
                try:
                    return config_class(**handler_config_data)
                except Exception as e:
                    logger.warning(f"创建 HandlerConfig 失败 {handler_path}: {e}，使用默认配置")
                    return config_class()
            
            # 如果都找不到，返回 None（框架会使用 BaseHandlerConfig 的默认行为）
            logger.debug(f"未找到 HandlerConfig 类 {handler_path}，使用默认配置")
            return None
            
        except Exception as e:
            logger.warning(f"解析 HandlerConfig 失败 {handler_path}: {e}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于序列化）
        
        Returns:
            配置字典
        """
        result = {
            "name": self.name,
            "description": self.description,
            "handler": self.handler_path,
            "dependencies": self.dependencies,
        }
        
        # ProviderConfig
        if self.provider_config.apis:
            result["provider_config"] = {
                "apis": [
                    {
                        "provider_name": api.provider_name,
                        "method": api.method,
                        "api_name": api.api_name,
                        "field_mapping": api.field_mapping,
                        "params": api.params,
                        "depends_on": api.depends_on,
                        "job_id": api.job_id,
                    }
                    for api in self.provider_config.apis
                ]
            }
        
        # HandlerConfig
        if self.handler_config:
            # 将 dataclass 转换为字典
            handler_config_dict = {
                k: v for k, v in self.handler_config.__dict__.items()
                if v is not None and not callable(v)
            }
            if handler_config_dict:
                result["handler_config"] = handler_config_dict
        
        return result
