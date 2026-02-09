import importlib.util
import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger
from core.infra.project_context import ConfigManager, PathManager
from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.config import DataSourceConfig

class DataSourceManagerHelper:
    """
    DataSource Helper class
    """
    def __init__(self):
        pass

    @staticmethod
    def load_mapping_from_py(mapping_path: Path) -> Dict[str, Any]:
        """
        从 mapping.py 加载 DATA_SOURCES。

        约定：mapping.py 中必须定义 DATA_SOURCES 字典，结构与原 mapping.json 的 data_sources 一致。
        """
        if not mapping_path.exists() or mapping_path.suffix != ".py":
            return None
        try:
            spec = importlib.util.spec_from_file_location("data_source_mapping", mapping_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            data_sources = getattr(mod, "DATA_SOURCES", None)
            if not isinstance(data_sources, dict):
                logger.warning(
                    f"mapping.py 中 DATA_SOURCES 必须是 dict，当前: {type(data_sources)}，路径: {mapping_path}"
                )
                return None
            return data_sources
        except Exception as e:
            logger.warning(f"加载 mapping.py 失败 {mapping_path}: {e}")
            return None

    @staticmethod
    def discover_mappings(mapping_path: Path):
        """
        发现并加载 mapping 配置。优先从 mapping.py 加载 DATA_SOURCES；
        若路径为 .json 则从 JSON 加载（兼容旧配置）。
        """
        if not mapping_path.exists():
            logger.error(f"❌ 数据源配置文件不存在: {mapping_path}")
            raise FileNotFoundError(f"data source mapping not found: {mapping_path}")

        if mapping_path.suffix == ".py":
            data_sources = DataSourceManagerHelper.load_mapping_from_py(mapping_path)
            if not data_sources:
                raise ValueError(f"mapping.py 未定义或无效的 DATA_SOURCES，路径: {mapping_path}")
        else:
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
    def load_config_from_py(config_path: Path) -> Dict[str, Any]:
        """
        从 handler 目录的 config.py 加载配置。

        约定：config.py 中必须定义 CONFIG 字典，框架原样使用，不解析 extra 等。
        """
        if not config_path.exists() or not config_path.suffix == ".py":
            return None
        try:
            spec = importlib.util.spec_from_file_location("handler_config", config_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            config = getattr(mod, "CONFIG", None)
            if not isinstance(config, dict):
                logger.warning(f"config.py 中 CONFIG 必须是 dict，当前: {type(config)}，路径: {config_path}")
                return None
            return {k: v for k, v in config.items() if not (isinstance(k, str) and k.startswith("_"))}
        except Exception as e:
            logger.warning(f"加载 config.py 失败 {config_path}: {e}")
            return None

    @staticmethod
    def load_config(config_path: Path) -> Dict[str, Any]:
        """
        Load the config from JSON (deprecated). Prefer load_config_from_py.
        """
        config: Dict[str, Any] = None
        if config_path.exists():
            raw = ConfigManager.load_json(config_path)
            config = {k: v for k, v in (raw or {}).items() if not k.startswith("_")}
        return config


    @staticmethod
    def find_handler_class_from_mappings(mapping: Dict[str, Any], name: str) -> Any:
        """
        根据 data_source 名称解析出 Handler 类。

        约定：
        - mapping 中的 handler 字段必须写成：
          - 完整路径: "userspace.data_source.handlers.kline.KlineHandler"
          - 或简写:   "kline.KlineHandler"
        """
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

        # 从 {name}.handler 模块加载类，无需各 handler 目录下的 __init__.py
        if module_path.startswith("userspace.data_source.handlers."):
            handler_module_path = module_path + ".handler"
        else:
            handler_module_path = module_path

        try:
            module = importlib.import_module(handler_module_path)
        except ImportError as e:
            logger.error(f"导入 Handler 模块失败 {handler_module_path}: {e}")
            return None

        handler_cls = getattr(module, class_name, None)
        if handler_cls is None:
            logger.error(f"在模块 {handler_module_path} 中未找到 Handler 类 {class_name}")
            return None
        return handler_cls


    @staticmethod
    def _find_handler_file_recursively(module_name: str) -> Optional[Path]:
        """
        递归查找 handler.py 文件
        
        Args:
            module_name: 简化的模块名（如 "kline_daily"）
        
        Returns:
            找到的 handler.py 文件路径，如果未找到则返回 None
        """
        handlers_dir = PathManager.data_source_handlers()
        if not handlers_dir.exists():
            return None
        
        # 递归查找所有包含 module_name 的目录下的 handler.py
        for path in handlers_dir.rglob(f"*/{module_name}/handler.py"):
            if path.exists() and path.is_file():
                return path
        
        # 也支持查找目录名完全匹配的情况
        for path in handlers_dir.rglob(f"{module_name}/handler.py"):
            if path.exists() and path.is_file():
                return path
        
        return None
    
    @staticmethod
    def _normalize_handler_path(handler_path: str) -> str:
        """
        标准化 handler 路径。

        支持三种形式：
        - 完整路径: "userspace.data_source.handlers.kline.KlineHandler"
        - 多级简写: "stock_klines.kline_daily.KlineDailyHandler"（支持嵌套目录）
        - 单级简写: "kline.KlineHandler"
        """
        # 已经是完整路径，直接返回
        if handler_path.startswith("userspace.data_source.handlers."):
            return handler_path

        parts = handler_path.split(".")
        if len(parts) < 2:
            logger.error(
                f"Handler 路径格式不正确: {handler_path}，"
                f"期望 'module.ClassName' 或 'userspace.data_source.handlers.module.ClassName'"
            )
            raise ValueError(f"Invalid handler path: {handler_path}")
        
        # 提取类名（最后一个部分）
        class_name = parts[-1]
        # 模块路径（除了类名之外的所有部分）
        module_parts = parts[:-1]
        
        # 构建完整路径
        module_path = ".".join(module_parts)
        return f"userspace.data_source.handlers.{module_path}.{class_name}"

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
    def create_handler_instance(
        handler_cls: Any,
        data_source_key: str,
        schema: Dict[str, Any],
        config: DataSourceConfig,
        providers: Dict[str, BaseProvider],
        depend_on_data_source_names: List[str] = None,
    ) -> Any:
        """
        Create the handler.

        schema: 表 schema 字典（来自 DataManager.get_table(name).load_schema()），非 DataSourceSchema。
        """
        if depend_on_data_source_names is None:
            depend_on_data_source_names = []
        try:
            handler_instance = handler_cls(
                data_source_key=data_source_key,
                schema=schema,
                config=config,
                providers=providers,
                depend_on_data_source_names=depend_on_data_source_names
            )
            return handler_instance
        except TypeError as e:
            raise ValueError(f"创建 Handler 实例失败: {e}")
        