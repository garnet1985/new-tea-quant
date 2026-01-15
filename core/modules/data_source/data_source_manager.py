"""
DataSource Manager - 数据源管理器

负责加载和管理 DataSource、Handler、Schema，执行数据获取
"""
import importlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger
from core.modules.data_manager import DataManager
from core.infra.project_context import ConfigManager, PathManager
from core.utils.util import merge_mapping_configs


class DataSourceManager:
    """
    数据源管理器
    
    职责：
    - 加载 Schema 定义
    - 加载 Handler 映射配置
    - 动态加载 Handler 类
    - 执行 Handler 获取数据
    """
    
    def __init__(self, is_verbose: bool = False):
        """
        初始化数据源管理器
        
        Args:
            is_verbose: 是否输出详细日志
        """
        # 统一使用 DataManager 单例作为数据访问入口
        self.data_manager = DataManager(is_verbose=False)
        self.is_verbose = is_verbose
        self._schemas: Dict[str, Any] = {}
        self._handlers: Dict[str, Any] = {}
        self._mapping: Dict[str, Any] = {}
        
        # 加载配置
        self._load_schemas()
        self._load_mapping()
        self._load_handlers()
    
    def _load_schemas(self):
        """加载 Schema 定义"""
        try:
            from core.modules.data_source.schemas import DEFAULT_SCHEMAS
            self._schemas = DEFAULT_SCHEMAS.copy()
        except Exception as e:
            logger.error(f"❌ 加载 Schema 失败: {e}")
            self._schemas = {}
    
    def _load_mapping(self):
        """
        加载 Handler 映射配置（先加载 defaults，再加载 custom 覆盖）
        
        使用 ConfigManager 统一配置加载和合并逻辑
        """
        # 1. 确定默认配置文件路径（优先使用 handlers/mapping.json）
        handlers_path = Path(__file__).parent / "handlers" / "mapping.json"
        defaults_path = Path(__file__).parent / "defaults" / "mapping.json"
        
        # 选择主要的默认配置文件
        default_path = handlers_path if handlers_path.exists() else defaults_path
        
        # 2. 确定用户配置文件路径（优先使用 userspace/data_source/mapping.json）
        user_path = PathManager.userspace() / "data_source" / "mapping.json"
        legacy_custom_path = Path(__file__).parent / "custom" / "mapping.json"
        
        # 3. 使用 ConfigManager 加载和合并配置
        # 注意：ConfigManager.load_with_defaults 只支持一个默认配置和一个用户配置
        # 对于多个默认配置的情况，我们需要先手动合并
        merged_config = {}
        
        # 3.1 加载主要的默认配置
        if default_path.exists():
            default_config = ConfigManager.load_json(default_path)
            merged_config = default_config.get("data_sources", {})
            logger.debug(f"✅ 加载了默认配置: {default_path.name}")
        
        # 3.2 如果存在另一个默认配置，合并它（兼容旧路径）
        if default_path == handlers_path and defaults_path.exists():
            legacy_default_config = ConfigManager.load_json(defaults_path)
            legacy_data_sources = legacy_default_config.get("data_sources", {})
            # 使用浅层合并（旧配置覆盖新配置，保持向后兼容）
            merged_config = {**merged_config, **legacy_data_sources}
            logger.debug(f"✅ 合并了兼容默认配置: {defaults_path.name}")
        
        # 3.3 加载并合并用户配置（使用深度合并）
        if user_path.exists():
            user_config = ConfigManager.load_json(user_path)
            user_data_sources = user_config.get("data_sources", {})
            # 使用 merge_mapping_configs 进行深度合并
            # params 需要深度合并，dependencies 需要完全覆盖
            merged_config = merge_mapping_configs(
                merged_config,
                user_data_sources,
                deep_merge_fields={"params"},
                override_fields={"dependencies"}
            )
            logger.debug(f"✅ 加载并合并了用户配置: {user_path}")
        
        # 3.4 如果存在旧路径的用户配置，也合并它（兼容旧路径）
        if legacy_custom_path.exists():
            legacy_user_config = ConfigManager.load_json(legacy_custom_path)
            legacy_user_data_sources = legacy_user_config.get("data_sources", {})
            # 使用 merge_mapping_configs 进行深度合并
            merged_config = merge_mapping_configs(
                merged_config,
                legacy_user_data_sources,
                deep_merge_fields={"params"},
                override_fields={"dependencies"}
            )
            logger.debug(f"✅ 合并了兼容用户配置: {legacy_custom_path.name}")
        
        # 4. 保存最终合并结果
        self._mapping = merged_config
    
    def _load_handler(self, ds_name: str, handler_path: str):
        """
        动态加载 Handler 类
        
        Args:
            ds_name: 数据源名称
            handler_path: Handler 类的完整路径（如 "defaults.handlers.stock_list_handler.TushareStockListHandler"）
        
        Returns:
            Handler 类
        """
        try:
            module_path, class_name = handler_path.rsplit('.', 1)
            module = importlib.import_module(f"core.modules.data_source.{module_path}")
            handler_class = getattr(module, class_name)
            if self.is_verbose:
                logger.debug(f"✅ 成功加载 Handler 类: {ds_name} ({handler_path})")
            return handler_class
        except Exception as e:
            logger.error(f"❌ 加载 Handler 失败 {ds_name} ({handler_path}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _load_handlers(self):
        """加载所有启用的 Handler 实例"""
        for ds_name, ds_config in self._mapping.items():
            if not ds_config.get("is_enabled", True):
                continue
            
            handler_path = ds_config.get("handler")
            if not handler_path:
                logger.warning(f"⚠️ {ds_name} 没有配置 handler")
                continue
            
            # 获取 Schema
            schema = self._schemas.get(ds_name)
            if not schema:
                logger.warning(f"⚠️ {ds_name} 没有找到对应的 Schema")
                continue
            
            # 加载 Handler 类
            handler_class = self._load_handler(ds_name, handler_path)
            if not handler_class:
                continue
            
            # 创建 Handler 实例
            try:
                params = ds_config.get("params", {})
                handler_instance = handler_class(schema, params, self.data_manager)
                
                # 如果是 RollingHandler，需要设置 data_source 名称
                if hasattr(handler_instance, 'set_data_source_name'):
                    handler_instance.set_data_source_name(ds_name)
                else:
                    # 其他 handler 的 data_source 应该是类属性，确保一致
                    handler_instance.data_source = ds_name
                
                self._handlers[ds_name] = handler_instance
                if self.is_verbose:
                    logger.debug(f"✅ 成功加载 Handler: {ds_name}")
            except Exception as e:
                logger.error(f"❌ 创建 Handler 实例失败 {ds_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    async def fetch(
        self, 
        ds_name: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        获取数据源数据（测试用 API）

        执行指定数据源的 Handler，获取并标准化数据。
        
        注意：
        - 数据保存由 Handler 在生命周期钩子中自行决定（如 after_normalize）
        - 此方法会检查 mapping.json 中的 is_enabled 配置，只有启用的 handler 才能执行
        
        Args:
            ds_name: 数据源名称
            context: 执行上下文（可选）
        
        Returns:
            标准化后的数据
        
        Raises:
            ValueError: 如果 handler 不存在或已被禁用
        """
        # 检查 handler 是否存在
        if ds_name not in self._mapping:
            raise ValueError(f"数据源 {ds_name} 未找到（mapping.json 中不存在）")
        
        # 检查 handler 是否被禁用
        handler_config = self._mapping[ds_name]
        if not handler_config.get("is_enabled", True):
            raise ValueError(f"数据源 {ds_name} 已被禁用（mapping.json 中 is_enabled: false）")
        
        # 检查 handler 是否已加载
        if ds_name not in self._handlers:
            raise ValueError(f"数据源 {ds_name} 的 Handler 未加载（可能配置错误或加载失败）")
        
        handler = self._handlers[ds_name]
        context = context or {}
        
        logger.info(f"🔄 开始获取数据源: {ds_name}")
        
        # 执行 Handler 的完整生命周期
        result = await handler.execute(context)
        
        logger.info(f"✅ 数据源 {ds_name} 获取完成")
        
        return result
    
    
    def list_data_sources(self) -> List[str]:
        """列出所有可用的数据源"""
        return list(self._handlers.keys())
    
    def get_handler_status(self) -> Dict[str, Any]:
        """
        获取所有数据源的加载状态（用于调试）
        
        Returns:
            Dict: {
                "mapping_count": int,  # mapping.json 中的数据源数量
                "enabled_count": int,    # 启用的数据源数量
                "schema_count": int,    # 有 schema 的数据源数量
                "loaded_handlers": List[str],  # 成功加载的 handler 列表
                "failed_handlers": Dict[str, str],  # 加载失败的 handler 及原因
            }
        """
        enabled_count = sum(1 for ds_config in self._mapping.values() 
                           if ds_config.get("is_enabled", True))
        schema_count = sum(1 for ds_name in self._mapping.keys() 
                          if ds_name in self._schemas)
        
        loaded_handlers = list(self._handlers.keys())
        failed_handlers = {}
        
        # 检查哪些数据源应该被加载但没有
        for ds_name, ds_config in self._mapping.items():
            if not ds_config.get("is_enabled", True):
                continue
            if ds_name not in self._handlers:
                reasons = []
                if not ds_config.get("handler"):
                    reasons.append("没有配置 handler")
                if ds_name not in self._schemas:
                    reasons.append("没有找到对应的 Schema")
                failed_handlers[ds_name] = "; ".join(reasons) if reasons else "未知原因"
        
        return {
            "mapping_count": len(self._mapping),
            "enabled_count": enabled_count,
            "schema_count": schema_count,
            "loaded_handlers": loaded_handlers,
            "failed_handlers": failed_handlers,
        }
    
    def get_schema(self, ds_name: str):
        """获取数据源的 Schema"""
        return self._schemas.get(ds_name)
    
    # ========== 依赖解析和注入 ==========
    
    # 全局依赖获取器注册表（可扩展）
    _DEPENDENCY_FETCHERS = {
        "latest_completed_trading_date": lambda dm: dm.service.calendar.get_latest_completed_trading_date(),
        "stock_list": lambda dm: dm.stock.list.load(filtered=True),
        # 未来可以添加：
        # "market_status": lambda dm: dm.get_market_status(),
        # "trading_calendar": lambda dm: dm.get_trading_calendar(),
    }
    
    def _resolve_global_dependencies(self) -> set:
        """
        解析所有启用的 handler 需要的全局依赖
        
        Returns:
            Set[str]: 需要获取的全局依赖名称集合
        """
        required_deps = set()
        
        for ds_name, ds_config in self._mapping.items():
            if not ds_config.get("is_enabled", True):
                continue
            
            # 获取 handler 声明的依赖需求
            dependencies = ds_config.get("dependencies", {})
            
            # 收集所有需要的依赖
            for dep_name, required in dependencies.items():
                if required:
                    required_deps.add(dep_name)
        
        if required_deps:
            logger.debug(f"📋 解析到需要获取的全局依赖: {', '.join(sorted(required_deps))}")
        else:
            logger.debug("📋 没有 handler 需要全局依赖")
        
        return required_deps
    
    def _fetch_global_dependencies(self, dep_names: set) -> Dict[str, Any]:
        """
        获取所有需要的全局依赖，构建 shared_context
        
        Args:
            dep_names: 需要获取的依赖名称集合
            
        Returns:
            Dict[str, Any]: shared_context，包含所有全局依赖
        """
        shared_context = {}
        
        for dep_name in dep_names:
            if dep_name in self._DEPENDENCY_FETCHERS:
                try:
                    fetcher = self._DEPENDENCY_FETCHERS[dep_name]
                    value = fetcher(self.data_manager)
                    shared_context[dep_name] = value
                    logger.debug(f"✅ 获取全局依赖: {dep_name}")
                except Exception as e:
                    logger.error(f"❌ 获取全局依赖失败 {dep_name}: {e}")
                    # 如果关键依赖获取失败，可以选择中断或继续
                    # 这里选择继续，让 handler 自己处理缺失的依赖
            else:
                logger.warning(f"⚠️ 未知的全局依赖: {dep_name}")
        
        return shared_context
    
    def _get_enabled_handlers(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有启用的 handler 配置
        
        Returns:
            Dict[str, Dict[str, Any]]: {handler_name: handler_config}
        """
        enabled_handlers = {}
        for ds_name, ds_config in self._mapping.items():
            if ds_config.get("is_enabled", True):
                enabled_handlers[ds_name] = ds_config
        return enabled_handlers

    async def renew_data(
        self,
        latest_completed_trading_date: str = None,
        stock_list: Optional[list] = None,
        test_mode: bool = False,
        dry_run: bool = False
    ):
        """
        一站式更新：行情数据 + 标签数据。

        Args:
            latest_completed_trading_date: 最新交易日（可选，如果不提供则自动获取）
            stock_list: 股票列表（可选，如果不提供则从数据库读取）
            test_mode: 测试模式，如果为 True，只处理前 10-20 个股票
            dry_run: 干运行模式，如果为 True，只更新行情流程，不写入任何标签
        """
        # Step 1: 依赖解析 - 解析所有启用的 handler 需要的全局依赖
        enabled_handlers = self._get_enabled_handlers()
        required_deps = self._resolve_global_dependencies()
        
        # Step 2: 依赖注入 - 获取所有需要的全局依赖，构建 shared_context
        shared_context = self._fetch_global_dependencies(required_deps)
        
        # 如果外部传入了 latest_completed_trading_date 或 stock_list，覆盖 shared_context
        if latest_completed_trading_date:
            shared_context["latest_completed_trading_date"] = latest_completed_trading_date
        if stock_list:
            shared_context["stock_list"] = stock_list
        
        # 添加执行参数
        shared_context.update({
            "test_mode": test_mode,
            "dry_run": dry_run,
        })
        
        logger.info(f"🚀 开始执行数据更新，共 {len(enabled_handlers)} 个启用的 handler")
        
        # Step 3: 遍历所有启用的 handler，执行 build context + fetch
        for handler_name, handler_config in enabled_handlers.items():
            if handler_name not in self._handlers:
                logger.warning(f"⚠️ Handler {handler_name} 未加载，跳过")
                continue
            
            handler = self._handlers[handler_name]
            
            try:
                logger.info(f"📊 处理数据源: {handler_name}")
                
                # 复制 shared_context，创建独立的 handler_context（避免污染）
                # handler_context 会在 execute 中传递给 handler.before_fetch
                handler_context = shared_context.copy()
                
                # Step 3: Handler Execution Layer
                # before_fetch 会在 execute 中调用（作为生命周期钩子）
                # 此时 handler_context 已经包含了所有全局依赖，handler 的 before_fetch
                # 可以从 context 中读取这些依赖，并添加自己的特定 context
                result = await self.fetch(handler_name, context=handler_context)
                
                logger.info(f"✅ 数据源 {handler_name} 处理完成")
                
            except Exception as e:
                logger.error(f"❌ 处理数据源 {handler_name} 失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        logger.info("🎉 所有数据源更新完成")
        
        # 等待所有批量写入完成（DuckDB 并发写入需要）
        if self.data_manager and self.data_manager.db:
            logger.info("⏳ 等待所有数据写入完成...")
            self.data_manager.db.wait_for_writes(timeout=60.0)
            logger.info("✅ 所有数据写入完成")
