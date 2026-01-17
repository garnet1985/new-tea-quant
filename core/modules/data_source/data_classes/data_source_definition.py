"""
DataSource Definition 核心类

标准化的 DataSource 配置对象，用于统一管理 DataSource 的配置。
"""
from dataclasses import dataclass, field, fields
from typing import Dict, Any, Optional, Type
from pathlib import Path
from loguru import logger

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
        
        # 验证 API 配置（在 handler_config 中）
        # 注意：某些自定义 Handler（如 PriceIndexesHandler、CorporateFinanceHandler）在代码中动态生成 API 调用，
        # 不需要在配置中定义 API，这是正常的。但如果配置了 API，handler 可以使用 get_api_job() 和 get_api_job_with_params() 方法。
        if self.handler_config and self.handler_config.apis:
            for name, api_config in self.handler_config.apis.items():
                if not isinstance(api_config, dict):
                    logger.error(f"API 配置 '{name}' 必须是字典格式，当前格式: {type(api_config).__name__}")
                    return False
                if not api_config.get("provider_name"):
                    logger.error(f"API 配置 '{name}' 的 provider_name 不能为空")
                    return False
                if not api_config.get("method"):
                    logger.error(f"API 配置 '{name}' 的 method 不能为空")
                    return False
        else:
            logger.debug(f"DataSourceDefinition {self.name} 没有配置任何 API（handler 将在代码中动态生成 API 调用）")
        
        return True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], name: Optional[str] = None) -> "DataSourceDefinition":
        """
        从字典创建 DataSourceDefinition
        
        配置格式：
        {
            "handler": "userspace.data_source.handlers.gdp.GdpHandler",
            "description": "...",
            "dependencies": {...},
            "handler_config": {
                "date_format": "quarter",
                "rolling_unit": "quarter",
                "rolling_length": 4,
                "apis": {
                    "gdp_data": {
                        "provider_name": "tushare",
                        "method": "get_gdp",
                        "field_mapping": {...},
                        "params": {...},
                        "depends_on": [...],
                        "api_name": "...",
                        "job_id": "..."
                    }
                },
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
        
        # 获取 handler_path（支持简化格式）
        handler_path = data.get("handler", "")
        if not handler_path:
            raise ValueError("DataSourceDefinition.handler_path 不能为空")
        
        # 如果 handler_path 是简化格式，自动补全为完整路径
        handler_path = cls._normalize_handler_path(handler_path)
        
        # 获取 description
        description = data.get("description", "")
        
        # 获取 dependencies
        dependencies = data.get("dependencies", {})
        
        # 解析 HandlerConfig（包含 API 配置）
        handler_config = cls._parse_handler_config(data, handler_path)
        
        # 获取原始 handler_config 字典（用于 get_param 访问自定义字段）
        handler_config_dict = data.get("handler_config", {})
        
        # 创建实例
        definition = cls(
            name=ds_name,
            handler_path=handler_path,
            description=description,
            handler_config=handler_config,
            _handler_config_dict=handler_config_dict,
            dependencies=dependencies,
        )
        
        # 验证
        if not definition.validate():
            logger.warning(f"DataSourceDefinition {ds_name} 验证失败，但继续创建")
        
        return definition
    
    @classmethod
    def _normalize_handler_path(cls, handler_path: str) -> str:
        """
        标准化 handler 路径
        
        支持简化格式：
        - "kline.KlineHandler" -> "userspace.data_source.handlers.kline.KlineHandler"
        - "kline" -> "userspace.data_source.handlers.kline.KlineHandler"（自动推断类名）
        - "userspace.data_source.handlers.kline.KlineHandler" -> 保持不变
        
        Args:
            handler_path: handler 路径（可能是简化格式）
        
        Returns:
            完整的 handler 路径
        """
        # 如果已经是完整路径，直接返回
        if handler_path.startswith("userspace.data_source.handlers."):
            return handler_path
        
        # 处理简化格式
        parts = handler_path.split(".")
        
        if len(parts) == 1:
            # 只有 handler 名称（如 "kline"），需要推断类名
            handler_name = parts[0]
            # 尝试从 handler.py 文件中查找类名
            class_name = cls._infer_handler_class_name(handler_name)
            if class_name:
                return f"userspace.data_source.handlers.{handler_name}.{class_name}"
            else:
                # 如果无法推断，使用默认命名规则：{HandlerName}Handler
                # 将 handler_name 转换为 PascalCase
                class_name = handler_name[0].upper() + handler_name[1:] + "Handler"
                return f"userspace.data_source.handlers.{handler_name}.{class_name}"
        elif len(parts) == 2:
            # handler 名称和类名（如 "kline.KlineHandler"）
            handler_name, class_name = parts
            return f"userspace.data_source.handlers.{handler_name}.{class_name}"
        else:
            # 其他格式，假设已经是完整路径或格式错误
            logger.warning(f"Handler 路径格式可能不正确: {handler_path}，保持原样")
            return handler_path
    
    @classmethod
    def _infer_handler_class_name(cls, handler_name: str) -> Optional[str]:
        """
        从 handler.py 文件推断 handler 类名
        
        Args:
            handler_name: handler 名称（如 "kline"）
        
        Returns:
            handler 类名，如果无法推断返回 None
        """
        try:
            handler_dir = PathManager.data_source_handler(handler_name)
            handler_file = handler_dir / "handler.py"
            
            if not handler_file.exists():
                return None
            
            # 解析 AST 查找继承自 BaseDataSourceHandler 的类
            import ast
            with open(handler_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(handler_file))
            
            # 查找继承自 BaseDataSourceHandler 的类
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 检查是否继承自 BaseDataSourceHandler
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            if base.id == "BaseDataSourceHandler":
                                return node.name
                        elif isinstance(base, ast.Attribute):
                            if base.attr == "BaseDataSourceHandler":
                                return node.name
            
            return None
        except Exception as e:
            logger.debug(f"推断 handler 类名失败 {handler_name}: {e}")
            return None
    
    @classmethod
    def _extract_handler_name(cls, handler_path: str) -> Optional[str]:
        """
        从 handler_path 提取 handler_name
        
        例如：
        - "userspace.data_source.handlers.kline.KlineHandler" -> "kline"
        - "userspace.data_source.handlers.gdp.GdpHandler" -> "gdp"
        
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
                # 过滤掉注释字段（_comment），避免传递给 Config 类
                config_data = {k: v for k, v in config_data.items() if not k.startswith("_")}
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
        2. 从 mapping.json 读取 handler_config
        3. 检查 handler 类是否定义了 config_class 属性
        4. 如果定义了 config_class，使用该 Config 类
        5. 如果没有定义 config_class，根据 renew_mode 自动选择对应的 Config 类
        6. mapping.json 中的 handler_config 覆盖 JSON 配置和 Config 类默认值
        
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
            
            # Step 2: 从 mapping.json 读取 handler_config
            mapping_config = data.get("handler_config", {})
            # 过滤掉注释字段（_comment），避免传递给 Config 类
            mapping_config = {k: v for k, v in mapping_config.items() if not k.startswith("_")}
            
            # Step 3: 合并配置（JSON 配置 → mapping.json 配置）
            # JSON 配置作为默认值，mapping.json 中的 handler_config 覆盖
            merged_config = {**json_config, **mapping_config}
            
            # 再次过滤 merged_config 中的注释字段（双重保险）
            merged_config = {k: v for k, v in merged_config.items() if not k.startswith("_")}
            
            # 从 merged_config 中提取 apis（apis 会直接放到 handler_config 中）
            apis_config = merged_config.pop("apis", None)
            # 验证 apis 格式（如果存在）
            if apis_config is not None and not isinstance(apis_config, dict):
                raise ValueError(
                    f"API 配置必须是字典格式（name -> 配置），当前格式: {type(apis_config).__name__}。"
                    f"示例: {{\"api_name\": {{\"provider_name\": \"tushare\", \"method\": \"get_data\"}}}}"
                )
            
            # Step 4: 检查 handler 类是否定义了 config_class 属性
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
            config_class = None
            if hasattr(handler_class, 'config_class'):
                config_class = getattr(handler_class, 'config_class')
                if config_class is None:
                    # config_class 被显式设置为 None，需要自动选择
                    config_class = None
                elif not issubclass(config_class, BaseHandlerConfig):
                    logger.warning(
                        f"Handler {handler_path} 的 config_class 不是 BaseHandlerConfig 的子类，"
                        f"跳过创建 HandlerConfig"
                    )
                    return None
            
            # Step 5: 如果没有定义 config_class，根据 renew_mode 自动选择
            if config_class is None:
                # 使用已过滤的 merged_config 来选择 config_class
                config_class = cls._select_config_class_by_renew_mode(merged_config, handler_path)
                if config_class is None:
                    # 无法自动选择，返回 None
                    return None
            
            # Step 6: 创建 HandlerConfig 实例
            # 最后一次过滤，确保没有 _comment 等注释字段
            final_config = {k: v for k, v in merged_config.items() if not k.startswith("_")}
            
            # 只保留 Config 类定义的字段，过滤掉 handler 特定的配置（如 api_fields）
            config_field_names = {f.name for f in fields(config_class)}
            filtered_final_config = {k: v for k, v in final_config.items() if k in config_field_names}
            
            try:
                handler_config_instance = config_class(**filtered_final_config)
                # 将 apis 配置添加到 handler_config 中
                if apis_config:
                    handler_config_instance.apis = apis_config
                return handler_config_instance
            except Exception as e:
                logger.warning(
                    f"创建 HandlerConfig 失败 {handler_path}: {e}，尝试使用默认配置"
                )
                # 如果合并后的配置创建失败，尝试只用 JSON 配置（也要过滤）
                try:
                    filtered_json_config = {k: v for k, v in json_config.items() if not k.startswith("_")} if json_config else {}
                    if filtered_json_config:
                        # 如果使用 JSON 配置，需要根据 JSON 配置的 renew_mode 重新选择 config_class
                        fallback_config_class = cls._select_config_class_by_renew_mode(filtered_json_config, handler_path)
                        if fallback_config_class:
                            # 只保留 Config 类定义的字段
                            fallback_config_field_names = {f.name for f in fields(fallback_config_class)}
                            filtered_fallback_config = {k: v for k, v in filtered_json_config.items() if k in fallback_config_field_names}
                            fallback_instance = fallback_config_class(**filtered_fallback_config)
                            # 将 apis 配置添加到 handler_config 中
                            if apis_config:
                                fallback_instance.apis = apis_config
                            return fallback_instance
                    # 如果 JSON 配置为空或选择失败，使用已选择的 config_class 的默认值
                    # 需要根据 config_class 类型设置正确的 renew_mode，避免验证失败
                    from core.modules.data_source.data_classes.handler_config import (
                        IncrementalConfig, RollingConfig, RefreshConfig
                    )
                    default_renew_mode = "rolling"  # BaseHandlerConfig 的默认值
                    if config_class == IncrementalConfig:
                        default_renew_mode = "incremental"
                    elif config_class == RollingConfig:
                        default_renew_mode = "rolling"
                    elif config_class == RefreshConfig:
                        default_renew_mode = "refresh"
                    fallback_instance = config_class(renew_mode=default_renew_mode)
                    # 将 apis 配置添加到 handler_config 中
                    if apis_config:
                        fallback_instance.apis = apis_config
                    return fallback_instance
                except Exception as fallback_error:
                    logger.warning(
                        f"使用 JSON 配置创建 HandlerConfig 也失败 {handler_path}: {fallback_error}，使用默认配置"
                    )
                    # 如果还是失败，使用 Config 类的默认值（需要设置正确的 renew_mode）
                    from core.modules.data_source.data_classes.handler_config import (
                        IncrementalConfig, RollingConfig, RefreshConfig
                    )
                    default_renew_mode = "rolling"  # BaseHandlerConfig 的默认值
                    if config_class == IncrementalConfig:
                        default_renew_mode = "incremental"
                    elif config_class == RollingConfig:
                        default_renew_mode = "rolling"
                    elif config_class == RefreshConfig:
                        default_renew_mode = "refresh"
                    final_instance = config_class(renew_mode=default_renew_mode)
                    # 将 apis 配置添加到 handler_config 中
                    if apis_config:
                        final_instance.apis = apis_config
                    return final_instance
            
        except Exception as e:
            logger.warning(f"解析 HandlerConfig 失败 {handler_path}: {e}")
            return None
    
    @classmethod
    def _select_config_class_by_renew_mode(
        cls, config: Dict[str, Any], handler_path: str
    ) -> Optional[type]:
        """
        根据 renew_mode 自动选择对应的 Config 类
        
        Args:
            config: 配置字典（包含 renew_mode）
            handler_path: Handler 路径（用于错误提示）
        
        Returns:
            Config 类（IncrementalConfig, RollingConfig, RefreshConfig），如果无法选择则返回 None
        """
        from core.modules.data_source.data_classes.handler_config import (
            IncrementalConfig, RollingConfig, RefreshConfig
        )
        
        renew_mode = config.get("renew_mode")
        
        # renew_mode 必须显式声明，不声明就报错拒绝执行
        if not renew_mode:
            logger.error(
                f"Handler {handler_path} 的 handler_config 中缺少必需的 'renew_mode' 字段。"
                f"请显式声明 renew_mode: 'incremental' | 'rolling' | 'refresh'"
            )
            raise ValueError(
                f"Handler {handler_path} 的 handler_config 中缺少必需的 'renew_mode' 字段"
            )
        
        # 根据 renew_mode 选择对应的 Config 类
        if renew_mode == "incremental":
            return IncrementalConfig
        elif renew_mode == "rolling":
            return RollingConfig
        elif renew_mode == "refresh":
            return RefreshConfig
        else:
            logger.error(
                f"Handler {handler_path} 的 renew_mode 值无效: {renew_mode}。"
                f"必须是 'incremental' | 'rolling' | 'refresh'"
            )
            raise ValueError(
                f"Handler {handler_path} 的 renew_mode 值无效: {renew_mode}。"
                f"必须是 'incremental' | 'rolling' | 'refresh'"
            )
    
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
        
        
        # HandlerConfig（包含 API 配置）
        if self.handler_config:
            # 将 dataclass 转换为字典
            handler_config_dict = {
                k: v for k, v in self.handler_config.__dict__.items()
                if v is not None and not callable(v)
            }
            # apis 已经在 handler_config 中，不需要单独处理
            if handler_config_dict:
                result["handler_config"] = handler_config_dict
        
        return result
