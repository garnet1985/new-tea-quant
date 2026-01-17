"""
DataSource Definition 核心类

标准化的 DataSource 配置对象，用于统一管理 DataSource 的配置。
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Type
from pathlib import Path
from loguru import logger

from .api_config import ApiConfig, ProviderConfig
from .handler_config import BaseHandlerConfig
from core.infra.discovery import ClassDiscovery, DiscoveryConfig
from core.infra.project_context import PathManager, ConfigManager


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
    
    handler_config: Optional[BaseHandlerConfig] = None  # Handler 特定配置（Config 对象或 None）
    _handler_config_dict: Dict[str, Any] = field(default_factory=dict)  # Handler 配置原始字典（从 mapping.json）
    
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
        # 注意：某些自定义 Handler（如 PriceIndexesHandler）在代码中动态生成 API 调用，
        # 不需要在配置中定义 API，这是正常的
        if not self.provider_config.apis:
            logger.debug(f"DataSourceDefinition {self.name} 没有配置任何 API（可能是自定义 Handler，在代码中动态生成 API）")
        
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
    def _extract_handler_name(cls, handler_path: str) -> Optional[str]:
        """
        从 handler_path 提取 handler_name
        
        例如：
        - "userspace.data_source.handlers.kline.KlineHandler" -> "kline"
        - "userspace.data_source.handlers.rolling.RollingHandler" -> "rolling"
        
        Args:
            handler_path: Handler 类的完整路径
        
        Returns:
            handler_name，如果无法提取则返回 None
        """
        try:
            # 解析路径：userspace.data_source.handlers.{handler_name}.{ClassName}
            parts = handler_path.split(".")
            if len(parts) >= 4 and parts[0] == "userspace" and parts[1] == "data_source" and parts[2] == "handlers":
                return parts[3]  # handler_name
            return None
        except Exception:
            return None
    
    @classmethod
    def _load_handler_config_json(cls, handler_name: str) -> Dict[str, Any]:
        """
        从 JSON 文件加载 Handler 的默认配置
        
        配置文件位置：userspace/data_source/handlers/{handler_name}/config.json
        
        Args:
            handler_name: Handler 名称（如 "kline"）
        
        Returns:
            配置字典，如果文件不存在或加载失败返回空字典
        """
        try:
            handler_dir = PathManager.data_source_handler(handler_name)
            config_json_path = handler_dir / "config.json"
            
            if not config_json_path.exists():
                return {}
            
            config_data = ConfigManager.load_json(config_json_path)
            if config_data:
                logger.debug(f"✅ 从 JSON 文件加载 Handler 配置: {handler_name}")
            return config_data
        except Exception as e:
            logger.debug(f"读取 Handler JSON 配置失败 {handler_name}: {e}")
            return {}
    
    @classmethod
    def _parse_handler_config(
        cls, data: Dict[str, Any], handler_path: str
    ) -> Optional[BaseHandlerConfig]:
        """
        解析 HandlerConfig
        
        配置读取顺序：
        1. 从 JSON 文件读取默认配置（handlers/{handler_name}/config.json）
        2. 检查 handler 类是否定义了 config_class 属性
        3. 如果定义了 config_class，创建 Config 实例（JSON 配置作为默认值）
        4. mapping.json 中的 handler_config 覆盖 JSON 配置和 Config 类默认值
        
        Args:
            data: 配置字典（包含 mapping.json 中的 handler_config）
            handler_path: Handler 路径（如 "userspace.data_source.handlers.kline.KlineHandler"）
        
        Returns:
            HandlerConfig 实例（如果找到对应的 Config 类），否则返回 None
        """
        try:
            # Step 1: 从 JSON 文件读取默认配置
            handler_name = cls._extract_handler_name(handler_path)
            json_config = {}
            if handler_name:
                json_config = cls._load_handler_config_json(handler_name)
            
            # Step 2: 检查 handler 类是否定义了 config_class 属性
            config = DiscoveryConfig(
                base_class=BaseHandlerConfig,
                module_name_pattern="",  # 不使用包扫描
            )
            discovery = ClassDiscovery(config)
            
            handler_class = discovery.discover_class_by_path(
                class_path=handler_path,
                base_class=None  # 不验证基类，因为我们要找的是 Handler 类
            )
            
            if not handler_class:
                # Handler 类本身不存在，直接返回 None
                return None
            
            # 检查是否有 config_class 属性
            if not hasattr(handler_class, 'config_class'):
                # Handler 没有定义 config_class，直接返回 None（不查找，不记录日志）
                return None
            
            config_class = getattr(handler_class, 'config_class')
            if config_class is None:
                # config_class 被显式设置为 None，返回 None
                return None
            
            # Handler 定义了 config_class，验证并创建实例
            if not issubclass(config_class, BaseHandlerConfig):
                logger.warning(
                    f"Handler {handler_path} 的 config_class 不是 BaseHandlerConfig 的子类，"
                    f"跳过创建 HandlerConfig"
                )
                return None
            
            # Step 3: 合并配置（JSON 配置 → mapping.json 配置）
            # JSON 配置作为默认值，mapping.json 中的 handler_config 覆盖
            mapping_config = data.get("handler_config", {})
            
            # 合并：JSON 配置（默认值）+ mapping.json 配置（覆盖）
            merged_config = {**json_config, **mapping_config}
            
            # Step 4: 创建 HandlerConfig 实例
            try:
                return config_class(**merged_config)
            except Exception as e:
                logger.warning(
                    f"创建 HandlerConfig 失败 {handler_path}: {e}，尝试使用默认配置"
                )
                # 如果合并后的配置创建失败，尝试只用 JSON 配置
                try:
                    return config_class(**json_config) if json_config else config_class()
                except Exception:
                    # 如果还是失败，使用 Config 类的默认值
                    return config_class()
            
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
