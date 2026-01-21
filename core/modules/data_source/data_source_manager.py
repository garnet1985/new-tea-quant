from typing import Dict, Any, List
from loguru import logger

from core.infra.project_context import PathManager
from core.infra.discovery import ModuleDiscovery
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.schema import DataSourceSchema
from core.modules.data_source.service.manager_helper import DataSourceManagerHelper
from core.modules.data_source.service.provider_helper import DataSourceProviderHelper
from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.data_class.config import DataSourceConfig

class DataSourceManager:
    """
    DataSource Manager class
    """
    def __init__(self):
        self.data_sources = []
        self.mappings = self._discover_mappings()
        self.handlers = self._discover_handlers()
        self.providers = self._discover_providers()

        self._schemas_cache: Dict[str, DataSourceSchema] = {}
        self._configs_cache: Dict[str, Any] = {}
        self._handlers_cache: Dict[str, BaseHandler] = {}

    def execute(self):
        self._flush_cache()
        self._refresh_handlers()
        for handler in self.handlers:
            handler.execute()

    def _refresh_handlers(self):
        self.mappings = self._discover_mappings()
        self.handlers = self._discover_handlers()

    def _flush_cache(self):
        self._schemas_cache.clear()
        self._configs_cache.clear()
        self._handlers_cache.clear()

    def _discover_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        发现并加载数据源的 mapping 配置。

        约定：
        - 使用 userspace/data_source/mapping.json 作为唯一入口
        - 返回值为 data_sources 字典或 None
        """
        mapping_path = PathManager.data_source_mapping()
        return DataSourceManagerHelper.discover_mappings(mapping_path)


    def _discover_handlers(self) -> List[BaseHandler]:
        handlers: List[BaseHandler] = []
        for data_source_name, data_source_config in self.mappings.items():
            if not data_source_config.get("is_enabled", True):
                logger.info(f"Data source {data_source_name} is disabled, skip")
                continue

            schema = self._discover_schema(data_source_name)
            if not schema:
                logger.error(f"Data source schema {data_source_name} 没有找到，跳过")
                continue

            config = self._discover_config(data_source_name)
            if config is None:
                logger.error(f"Data source config {data_source_name} 没有找到，跳过")
                continue

            handler = self._discover_handler(data_source_name, schema, config)
            if not handler:
                logger.error(f"Data source handler {data_source_name} 没有找到，跳过")
                continue

            handlers.append(handler)

        return handlers

    def _discover_schema(self, data_source_name: str) -> Any:
        """
        为指定的数据源发现并返回 Schema 定义对象。

        约定：
        - 每个 handler 目录下有一个 schema.py
        - 其中定义了名为 SCHEMA 的对象（通常是 DataSourceSchema 实例）
        - 该 SCHEMA 的 name 属性等于 data_source_name
        """
        if data_source_name in self._schemas_cache:
            return self._schemas_cache[data_source_name]

        discovery = ModuleDiscovery()
        self._schemas_cache = discovery.discover_objects(
            base_module_path="userspace.data_source.handlers",
            object_name="SCHEMA",
            module_pattern="{base_module}.{name}.schema",
        )

        schema = DataSourceManagerHelper.get_schema_by_name(self._schemas_cache, data_source_name)

        if not schema:
            logger.warning(f"未找到数据源 '{data_source_name}' 对应的 Schema")
            return None

        # 显式验证 Schema 完整性（严重问题会抛出异常并停止执行）
        schema.validate()

        return schema



    def _discover_config(self, data_source_name: str) -> Any:
        """
        发现并加载指定数据源的 Config 配置。

        当前约定：
        - 每个 handler 目录下有一个 config.json：
          userspace/data_source/handlers/{data_source_name}/config.json
        - Config 目前先以原始 dict 形式返回，后续可以在此基础上封装为 dataclass。
        """
        # 简单缓存，避免同一进程内重复读取磁盘
        if data_source_name in self._configs_cache:
            return self._configs_cache[data_source_name]

        handler_dir = PathManager.data_source_handler(data_source_name)
        config_path = handler_dir / "config.json"

        config_dict = DataSourceManagerHelper.load_config(config_path)

        if not config_dict:
            logger.info(f"Data source {data_source_name} 未找到 config.json，跳过")
            return None

        # 创建 DataSourceConfig 实例（内部会自动验证配置）
        config = DataSourceConfig(config_dict, data_source_name=data_source_name)

        # 显式验证 Config 完整性（虽然 __init__ 中已调用，但这里显式调用以确保：
        # 1. 代码可读性：明确告知这里会验证配置
        # 2. 严重问题会抛出 ValueError 并停止执行（已在 validate() 中实现）
        config.validate()

        self._configs_cache[data_source_name] = config
        return config


    def _discover_handler(
        self,
        data_source_name: str,
        schema: DataSourceSchema,
        config: Any,  # DataSourceConfig 实例或 Dict[str, Any]
    ) -> Any:
        """
        基于 mapping 信息、Schema 和 Config 实例化具体的 Handler。

        步骤大纲：
        1. 从 self.mappings 中读取 handler 路径（支持简化格式）
        2. 使用 DataSourceDefinition._normalize_handler_path 标准化为完整模块路径
        3. 动态 import 模块并获取 Handler 类
        4. 使用 (data_source_name, schema, config) 构造 Handler 实例
        5. 返回 Handler 实例，并写入缓存
        """
        # 简单缓存：同一 data_source_name 只创建一次实例
        if data_source_name in self._handlers_cache:
            return self._handlers_cache[data_source_name]

        handler_cls = DataSourceManagerHelper.resolve_handler_by_name(self.mappings, data_source_name)

        if not DataSourceManagerHelper.is_valid_handler(handler_cls):
            return None

        handler_instance = DataSourceManagerHelper.create_handler(handler_cls, data_source_name, schema, config)

        if handler_instance:
            self._handlers_cache[data_source_name] = handler_instance
            return handler_instance

        return None

    def _discover_providers(self) -> Dict[str, BaseProvider]:
        """
        发现并实例化可用的 Provider。

        约定：
        - 这里不做按 data_source 过滤，直接把当前项目中能发现的 Provider 全部注册好；
        - 步骤由多个 helper 函数组成，便于阅读整体流程；
        - 后续 handler/helper 可以根据需要从 self.providers 中按名称取用。
        """
        # 1. 发现所有 Provider 类
        provider_classes = DataSourceProviderHelper.discover_provider_classes()

        providers: Dict[str, BaseProvider] = {}

        # 2. 实例化所有 Provider（认证配置由 BaseProvider 自动处理）
        for provider_name, provider_class in provider_classes.items():
            instance = DataSourceProviderHelper.create_provider_instance(provider_name, provider_class)
            if instance is not None:
                providers[provider_name] = instance

        return providers

 