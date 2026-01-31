from typing import Dict, Any, List, Tuple
from loguru import logger

from core.infra.project_context import PathManager
from core.modules.data_manager.data_manager import DataManager
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.handler_mapping import HandlerMapping
from core.modules.data_source.execution_scheduler import DataSourceExecutionScheduler
from core.modules.data_source.service.manager_helper import DataSourceManagerHelper
from core.modules.data_source.service.provider_helper import DataSourceProviderHelper
from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.data_class.config import DataSourceConfig

class DataSourceManager:
    """
    DataSource Manager class
    """
    def __init__(self, is_verbose: bool = False):
        """
        初始化 DataSource Manager
        
        Args:
            is_verbose: 是否显示详细日志（保留参数以兼容现有代码）
        """
        self._all_valid_configs_cache: Dict[str, DataSourceConfig] = {}
        self._all_valid_handlers_cache: Dict[str, Any] = {}

        self._execution_scheduler = DataSourceExecutionScheduler()


    def execute(self):
        self._flush_cache()
        mappings = self._discover_mappings()
        providers = self._discover_providers()
        handler_instances = self._discover_handlers(mappings, providers)
        self._execution_scheduler.run(handler_instances, mappings)

    def _flush_cache(self):
        self._all_valid_configs_cache.clear()
        self._all_valid_handlers_cache.clear()

    def _discover_mappings(self) -> HandlerMapping:
        """
        发现并加载数据源的 mapping 配置。

        约定：
        - 使用 userspace/data_source/mapping.py（DATA_SOURCES）作为入口；兼容 mapping.json。
        - 返回 HandlerMapping(data_sources=...)
        """
        mapping_path = PathManager.data_source_mapping()
        mapping = DataSourceManagerHelper.discover_mappings(mapping_path)
        return HandlerMapping(data_sources=mapping)


    def _discover_handlers(self, mappings: HandlerMapping, providers: Dict[str, BaseProvider]) -> List[BaseHandler]:
        handler_instances = []

        for data_source_key in mappings.get_enabled().keys():
            config = self._discover_config(data_source_key)
            if config is None:
                logger.error(f"Data source config {data_source_key} 没有找到，跳过")
                continue

            schema = self._get_schema_for_handler(config)
            if not schema:
                logger.error(f"Data source {data_source_key} 无法从绑定表加载 schema，跳过")
                continue

            handler_cls = self._discover_handler(data_source_key, mappings)
            if not handler_cls:
                logger.error(f"Data source handler {data_source_key} 没有找到，跳过")
                continue

            handler_instance = DataSourceManagerHelper.create_handler_instance(
                handler_cls,
                data_source_key,
                schema,
                config,
                providers,
                mappings.get_depend_on_data_source_names(data_source_key),
            )
            if not handler_instance:
                logger.error(f"Data source handler instance {data_source_key} 创建失败，跳过")
                continue

            handler_instances.append(handler_instance)

        return handler_instances

    def _get_schema_for_handler(self, config: DataSourceConfig) -> Dict[str, Any]:
        """
        根据 config 的顶层 table 从 DataManager 加载表 schema（dict）。
        """
        table_name = config.get_table_name()
        if not table_name:
            return None
        try:
            data_manager = DataManager.get_instance()
            model = data_manager.get_table(table_name)
            if not model:
                logger.warning(f"表 '{table_name}' 未注册，无法加载 schema")
                return None
            return model.load_schema()
        except Exception as e:
            logger.warning(f"加载表 schema 失败 table={table_name}: {e}")
            return None

    def _discover_config(self, data_source_key: str) -> Any:
        """
        发现并加载指定数据源的 Config。仅支持 config.py，其中必须定义 CONFIG 字典。
        """
        if data_source_key in self._all_valid_configs_cache:
            return self._all_valid_configs_cache[data_source_key]

        handler_dir = PathManager.data_source_handler(data_source_key)
        config_path = handler_dir / "config.py"

        config_dict = DataSourceManagerHelper.load_config_from_py(config_path)
        if not config_dict:
            logger.info(f"Data source {data_source_key} 未找到或无法加载 config.py，跳过")
            return None

        config = DataSourceConfig(config_dict, data_source_key=data_source_key)
        if not config.is_valid():
            logger.warning(f"Data source {data_source_key} 的 config 不完整，跳过")
            return None

        self._all_valid_configs_cache[data_source_key] = config
        return config


    def _discover_handler(
        self,
        data_source_key: str,
        mappings: HandlerMapping,
    ) -> Any:
        """
        基于 mapping 信息、Schema 和 Config 实例化具体的 Handler。

        步骤大纲：
        1. 从 self.mappings 中读取 handler 路径（支持简化格式）
        2. 使用 DataSourceDefinition._normalize_handler_path 标准化为完整模块路径
        3. 动态 import 模块并获取 Handler 类
        4. 使用 (data_source_key, schema, config) 构造 Handler 实例
        5. 返回 Handler 实例，并写入缓存
        """
        # 简单缓存：同一 data_source_key 只创建一次实例
        if data_source_key in self._all_valid_handlers_cache:
            return self._all_valid_handlers_cache[data_source_key]

        handler_info = mappings.get_handler_info(data_source_key)
        handler_cls = DataSourceManagerHelper.find_handler_class_from_mappings(handler_info, data_source_key)

        if not DataSourceManagerHelper.is_valid_handler(handler_cls):
            return None

        self._all_valid_handlers_cache[data_source_key] = handler_cls
        return handler_cls

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

 