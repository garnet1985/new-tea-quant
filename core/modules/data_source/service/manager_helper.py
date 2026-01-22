import importlib
from pathlib import Path
from typing import Any, Dict
from loguru import logger
from core.infra.project_context import ConfigManager
from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.schema import DataSourceSchema

class DataSourceManagerHelper:
    """
    DataSource Helper class
    """
    def __init__(self):
        pass

    @staticmethod
    def discover_mappings(mapping_path: Path):
        """
        Discover the mappings
        """
        if not mapping_path.exists():
            logger.error(f"❌ 数据源配置文件不存在: {mapping_path}")
            raise FileNotFoundError(f"data source mapping.json not found: {mapping_path}")

        raw = ConfigManager.load_json(mapping_path)
        data_sources = raw.get("data_sources", {})

        if not isinstance(data_sources, dict):
            raise ValueError(
                f"data_sources 字段必须是对象(dict)，当前类型: {type(data_sources)}，文件: {mapping_path}"
            )

        # 轻度校验：每个 data source 至少要有 handler 字段
        for name, cfg in data_sources.items():
            if not isinstance(cfg, dict):
                logger.error(f"❌ data source '{name}' 的配置必须是对象(dict)，当前类型: {type(cfg)}")
                raise ValueError(f"invalid config for data source '{name}'")
            if "handler" not in cfg:
                logger.error(f"❌ data source '{name}' 缺少必需字段 'handler'")
                raise ValueError(f"data source '{name}' must define 'handler'")

        return data_sources

    @staticmethod
    def get_schema_by_name(objects: Dict[str, Any], name: str) -> Any:
        """ 
        Get the schema by name
        """
        for handler_name, schema in objects.items():
            schema_name = getattr(schema, "name", None)
            if schema_name == name:
                return schema
        return None

    @staticmethod
    def load_config(config_path: Path) -> Dict[str, Any]:
        """
        Load the config
        """
        config: Dict[str, Any] = None
        if config_path.exists():
            raw = ConfigManager.load_json(config_path)
            config = {k: v for k, v in (raw or {}).items() if not k.startswith("_")}
        return config


    @staticmethod
    def resolve_handler_by_name(mappings: Dict[str, Any], name: str) -> Any:
        """
        根据 data_source 名称解析出 Handler 类。

        约定：
        - mapping 中的 handler 字段必须写成：
          - 完整路径: "userspace.data_source.handlers.kline.KlineHandler"
          - 或简写:   "kline.KlineHandler"
        """
        mapping = mappings.get(name, {})
        handler_path_raw = mapping.get("handler")
        if not handler_path_raw:
            logger.error(f"Data source {name} 在 mapping 中未配置 handler 路径")
            return None

        # 标准化 handler 路径（支持简化格式）
        full_handler_path = DataSourceManagerHelper._normalize_handler_path(handler_path_raw)

        try:
            module_path, class_name = full_handler_path.rsplit(".", 1)
        except ValueError:
            logger.error(f"Handler 路径格式不正确: {full_handler_path}")
            return None

        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            logger.error(f"导入 Handler 模块失败 {module_path}: {e}")
            return None

        handler_cls = getattr(module, class_name, None)
        if handler_cls is None:
            logger.error(f"在模块 {module_path} 中未找到 Handler 类 {class_name}")
            return None
        return handler_cls


    @staticmethod
    def _normalize_handler_path(handler_path: str) -> str:
        """
        标准化 handler 路径。

        只支持两种形式：
        - 完整路径: "userspace.data_source.handlers.kline.KlineHandler"
        - 简写:     "kline.KlineHandler"
        """
        # 已经是完整路径，直接返回
        if handler_path.startswith("userspace.data_source.handlers."):
            return handler_path

        parts = handler_path.split(".")
        if len(parts) == 2:
            module_name, class_name = parts
            return f"userspace.data_source.handlers.{module_name}.{class_name}"

        logger.error(
            f"Handler 路径格式不正确: {handler_path}，"
            f"期望 'module.ClassName' 或 'userspace.data_source.handlers.module.ClassName'"
        )
        raise ValueError(f"Invalid handler path: {handler_path}")

    @staticmethod
    def is_valid_handler(handler_cls: Any) -> bool:
        """
        Check if the handler is valid
        """
        if not handler_cls:
            return False
        if not isinstance(handler_cls, type):
            return False
        if not issubclass(handler_cls, BaseHandler):
            return False
        return True

    @staticmethod
    def create_handler(handler_cls: Any, data_source_name: str, schema: DataSourceSchema, config: Dict[str, Any], providers: Dict[str, BaseProvider] = None) -> Any:
        """
        Create the handler
        
        Args:
            handler_cls: Handler 类
            data_source_name: 数据源名称
            schema: Schema 实例
            config: Config 实例或字典
            providers: Provider 字典（可选，新架构需要）
        """
        try:
            # 尝试新架构的签名（4个参数）
            handler_instance = handler_cls(
                data_source_name=data_source_name,
                schema=schema,
                config=config,
                providers=providers or {},
            )
        except TypeError as e:
            # 如果失败，可能是旧架构的 Handler，尝试旧签名
            try:
                # 旧架构：只传 schema, data_manager, definition
                from core.modules.data_manager.data_manager import DataManager
                handler_instance = handler_cls(
                    schema=schema,
                    data_manager=DataManager.get_instance(),
                    definition=None,
                )
            except TypeError as e2:
                # 兼容现有 Handler 还未迁移到新 BaseHandler 的情况，先给出明确提示
                logger.error(
                    f"构造 Handler {handler_cls} 失败，签名可能与 "
                    f"(data_source_name, schema, config, providers) 或 (schema, data_manager, definition) 不匹配: {e}, {e2}"
                )
                return None
        return handler_instance

    # Provider 相关的 helper 已迁移到 provider_helper.py 中