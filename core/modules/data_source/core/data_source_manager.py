from typing import Dict, Any, List, Tuple, Optional, Sequence
from pathlib import Path
import logging



from core.modules.data_manager import DataManager
from core.modules.data_source.core.base_class.base_provider import BaseProvider
from core.modules.data_source.core.data_class.handler_mapping import HandlerMapping
from core.modules.data_source.core.execution_scheduler import DataSourceExecutionScheduler
from core.modules.data_source.core.reserved_dependencies import RESERVED_DEPENDENCY_KEYS
from core.modules.data_source.core.service.manager_helper import DataSourceManagerHelper
from core.modules.data_source.core.service.provider_helper import DataSourceProviderHelper
from core.modules.data_source.core.base_class.base_handler import BaseHandler
from core.modules.data_source.core.data_class.config import DataSourceConfig
from core.modules.data_source.core.data_class.error import DataSourceConfigError
from core.infra.project_context import ProjectContext
from core.infra.discovery import Discovery


logger = logging.getLogger(__name__)


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

    def renew(
        self,
        table_name: Optional[str] = None,
        *,
        force: bool = False,
    ) -> None:
        """
        按配置 renew 数据（CLI / 脚本统一入口）。

        Args:
            table_name: 绑定表名（如 ``sys_stock_klines``）或 data source key（如 ``stock_klines``）。
                ``None`` 表示所有 ``is_enabled`` 的数据源。
            force: 强制 refresh：从 ``default_start_date`` 重拉，跳过日缓存与 ``renew_if_over_days``。
        """
        if table_name:
            key = self.resolve_renew_target(table_name)
            self.execute(sources=(key,), force=force)
            return
        self.execute(sources=None, force=force)

    def resolve_renew_target(self, table_or_source: str) -> str:
        """
        将表名或 data source key 解析为 mapping 中的 data source key。

        Raises:
            ValueError: 未启用或不存在。
        """
        name = str(table_or_source or "").strip()
        if not name:
            raise ValueError("table_name 不能为空")

        self._flush_cache()
        mappings = self._discover_mappings()
        enabled = mappings.get_enabled()
        if name in enabled:
            return name

        for key in enabled:
            cfg = self._discover_config(key)
            if cfg and cfg.get_table_name() == name:
                return key

        raise ValueError(
            f"未找到表或数据源: {name}\n{self.format_renew_targets_help()}"
        )

    def list_renew_targets(self) -> List[Dict[str, str]]:
        """已启用 renew 目标：``source``（key）与 ``table``（绑定表名）。"""
        self._flush_cache()
        mappings = self._discover_mappings()
        rows: List[Dict[str, str]] = []
        for key in sorted(mappings.get_enabled().keys()):
            cfg = self._discover_config(key)
            rows.append(
                {
                    "source": key,
                    "table": str(cfg.get_table_name() if cfg else ""),
                }
            )
        return rows

    @classmethod
    def format_renew_targets_help(cls) -> str:
        """格式化 renew 可选表名，供 CLI 报错提示。"""
        mgr = cls(is_verbose=False)
        lines = ["可选表名 / data source key："]
        for row in mgr.list_renew_targets():
            table = row.get("table") or "?"
            source = row.get("source") or "?"
            if table == source:
                lines.append(f"  - {table}")
            else:
                lines.append(f"  - {table}  (source: {source})")
        return "\n".join(lines)

    def execute(
        self,
        sources: Optional[Sequence[str]] = None,
        *,
        force: bool = False,
    ):
        """
        执行数据源：发现 mapping/config/handler → 按依赖顺序执行。

        对外推荐 ``renew(table_name=..., force=...)``；本方法供多源或内部调度。

        Args:
            sources: 仅执行这些 data source key；``None`` 表示全部已启用。
            force: 强制全量重拉（见 ``renew``）。

        是否写库由各 handler 的 config 顶层 is_dry_run 控制（True 则不执行 DB 写入）。
        """
        self._flush_cache()
        mappings = self._discover_mappings()
        providers = self._discover_providers()
        handler_instances = self._discover_handlers(mappings, providers)
        enabled = set(mappings.get_enabled().keys())
        by_key = {h.get_key(): h for h in handler_instances if h.get_key()}

        if force:
            self._clear_force_refresh_caches(sources, enabled)

        if sources:
            keys = tuple(str(k).strip() for k in sources if str(k).strip())
            unknown = [k for k in keys if k not in enabled]
            if unknown:
                raise ValueError(
                    f"未知或未启用的 data source: {unknown}；可选: {sorted(enabled)}"
                )
            self._execute_source_subset(keys, mappings, by_key, force=force)
            return

        self._execution_scheduler.run(handler_instances, mappings, force=force)

    @staticmethod
    def list_enabled_source_keys() -> List[str]:
        """返回 mapping 中已启用的 data source key 列表。"""
        mapping_path = ProjectContext.path.get_data_source_mapping_path()
        mapping = DataSourceManagerHelper.discover_mappings(mapping_path)
        return sorted(HandlerMapping(data_sources=mapping).get_enabled().keys())

    def _clear_force_refresh_caches(
        self,
        sources: Optional[Sequence[str]],
        enabled: set,
    ) -> None:
        """强制刷新时清理会短路 API 的 sys_cache 项。"""
        run_list = sources is None or "stock_list" in set(sources or ())
        if not run_list or "stock_list" not in enabled:
            return
        try:
            dm = DataManager.get_instance()
            if dm and dm.db_cache:
                dm.db_cache.delete("stock_list_last_update")
                logger.info("force_refresh：已清除 stock_list 日缓存")
        except Exception as e:
            logger.warning("force_refresh：清除 stock_list 缓存失败: %s", e)

    def _execute_source_subset(
        self,
        keys: Tuple[str, ...],
        mappings: HandlerMapping,
        by_key: Dict[str, BaseHandler],
        *,
        force: bool,
    ) -> None:
        """只执行指定 data source；依赖从缓存或 DB 注入。"""
        from core.modules.data_source.core.reserved_dependencies import resolve_reserved_dependency

        missing = [k for k in keys if k not in by_key]
        if missing:
            raise ValueError(f"Handler 未就绪: {missing}")

        dm = DataManager.get_instance()
        if dm is None:
            dm = DataManager(is_verbose=False)
            dm.initialize()

        scheduler = self._execution_scheduler
        scheduler.mappings = mappings

        need_list = any(
            "stock_list" in mappings.get_depend_on_data_source_names(k)
            for k in keys
        )
        if need_list and "stock_list" not in keys:
            from core.modules.data_source.core.service.sample_stock_list import is_sample_active

            rows = dm.stock.list.load_all()
            scheduler._dependency_cache["stock_list"] = rows
            suffix = "（样本）" if is_sample_active() else ""
            logger.info("从 DB 注入 stock_list 依赖：%s 只%s", len(rows), suffix)

        handlers_for_topo = [by_key[k] for k in keys]
        if need_list and "stock_list" not in keys and "stock_list" in by_key:
            handlers_for_topo = [by_key["stock_list"]] + handlers_for_topo

        sorted_all = scheduler._preprocess(handlers_for_topo)
        sorted_handlers = [h for h in sorted_all if h.get_key() in keys]

        preserved_list = (
            scheduler._dependency_cache.get("stock_list")
            if need_list and "stock_list" not in keys
            else None
        )
        scheduler._dependency_cache.clear()
        if preserved_list is not None:
            scheduler._dependency_cache["stock_list"] = preserved_list
        scheduler._failed_data_sources.clear()

        total = len(sorted_handlers)
        for idx, handler in enumerate(sorted_handlers):
            key = handler.get_key()
            logger.info("执行数据源 [%s/%s]: %s", idx + 1, total, key)
            deps: Dict[str, Any] = {}
            for dep_name in mappings.get_depend_on_data_source_names(key):
                if dep_name in RESERVED_DEPENDENCY_KEYS:
                    deps[dep_name] = resolve_reserved_dependency(dep_name)
                elif dep_name in scheduler._dependency_cache:
                    deps[dep_name] = scheduler._dependency_cache[dep_name]
                else:
                    raise ValueError(f"依赖未就绪: {key} -> {dep_name}（请先执行 {dep_name}）")
            if force:
                deps["_execution"] = {"force_refresh": True}
            result = handler.execute(deps)
            if mappings.is_dependency_for_downstream(key):
                if result and "data" in result:
                    scheduler._dependency_cache[key] = result["data"]
            logger.info("完成: %s", key)

        scheduler._retry_failed_data_sources()

    def _flush_cache(self):
        self._all_valid_configs_cache.clear()
        self._all_valid_handlers_cache.clear()

    def _discover_mappings(self) -> HandlerMapping:
        """
        发现并加载数据源的 mapping 配置。

        约定：
        - 使用 userspace/extensions/data_source/mapping.py（DATA_SOURCES）作为入口。
        - 返回 HandlerMapping(data_sources=...)
        """
        mapping_path = ProjectContext.path.get_data_source_mapping_path()
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
        
        支持递归查找：
        1. 首先尝试 handlers/{data_source_key}/config.py
        2. 找不到则递归搜索 handlers 下含该 key 的目录
        """
        if data_source_key in self._all_valid_configs_cache:
            return self._all_valid_configs_cache[data_source_key]

        # 首先尝试直接路径
        handler_dir = ProjectContext.path.get_data_source_handler_directory(data_source_key)
        config_path = handler_dir / "config.py"
        
        config_dict = DataSourceManagerHelper.load_config_from_py(config_path)
        
        # 如果直接路径找不到，尝试递归查找
        if not config_dict:
            config_path = self._find_config_recursively(data_source_key)
            if config_path:
                config_dict = DataSourceManagerHelper.load_config_from_py(config_path)
        
        if not config_dict:
            logger.info(f"Data source {data_source_key} 未找到或无法加载 config.py，跳过")
            return None

        try:
            config = DataSourceConfig.from_dict(config_dict, data_source_key)
        except DataSourceConfigError as e:
            logger.error(f"Data source {data_source_key} 配置错误: {e}")
            return None

        self._all_valid_configs_cache[data_source_key] = config
        return config
    
    def _find_config_recursively(self, data_source_key: str) -> Optional[Path]:
        """在 handlers 树中按目录名 key 定位 config.py。"""
        from core.infra.discovery import Discovery

        handlers_dir = ProjectContext.path.get_data_source_handlers_directory()
        return Discovery.file.find_in_tree(handlers_dir, data_source_key, "config.py")


    def _discover_handler(
        self,
        data_source_key: str,
        mappings: HandlerMapping,
    ) -> Any:
        """
        基于 mapping 信息、Schema 和 Config 实例化具体的 Handler。

        步骤大纲：
        1. 从 self.mappings 中读取 handler 路径（支持简化格式）
        2. 使用 DataSourceManagerHelper._normalize_handler_path 标准化为完整模块路径
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

    @staticmethod
    def get_data_end_meta(data_manager=None) -> Dict[str, Any]:
        """数据截断 / 有效结束日摘要（供 scan UI / catalog）。"""
        from core.modules.data_source.core.catalog.freshness_probe import get_data_end_meta

        return get_data_end_meta(data_manager)

    @staticmethod
    def resolve_freshness_end_date(data_manager=None) -> str:
        """有效 freshness 结束日（对齐 ``data.json`` as_of 与交易日历）。"""
        from core.modules.data_source.core.catalog.freshness_probe import (
            _resolve_freshness_end_date,
        )

        return _resolve_freshness_end_date(data_manager)

 