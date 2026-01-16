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
from core.modules.data_source.definition import DataSourceDefinition


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
        self._mapping: Dict[str, Any] = {}  # 原始配置（向后兼容）
        self._definitions: Dict[str, DataSourceDefinition] = {}  # 标准化的定义对象
        
        # 加载配置
        self._load_schemas()
        self._load_mapping()
        self._load_definitions()  # 将配置转换为 DataSourceDefinition
        self._load_handlers()
    
    def _load_schemas(self):
        """
        从 userspace 加载 Schema 定义
        
        每个 handler 目录下应该有 schema.py 文件，定义该 data source 的 schema
        """
        self._schemas = {}
        handlers_dir = PathManager.data_source_handlers()
        
        if not handlers_dir.exists():
            logger.warning(f"⚠️  Handlers 目录不存在: {handlers_dir}")
            return
        
        # 遍历所有 handler 目录，加载 schema
        for handler_dir in handlers_dir.iterdir():
            if not handler_dir.is_dir() or handler_dir.name.startswith('_'):
                continue
            
            schema_file = handler_dir / "schema.py"
            if not schema_file.exists():
                logger.debug(f"⚠️  {handler_dir.name} 没有 schema.py 文件，跳过")
                continue
            
            try:
                # 动态导入 schema 模块
                # 路径格式：userspace.data_source.handlers.{handler_name}.schema
                module_path = f"userspace.data_source.handlers.{handler_dir.name}.schema"
                schema_module = importlib.import_module(module_path)
                
                if hasattr(schema_module, 'SCHEMA'):
                    schema = schema_module.SCHEMA
                    schema_name = schema.name
                    self._schemas[schema_name] = schema
                    if self.is_verbose:
                        logger.debug(f"✅ 加载 Schema: {schema_name} (from {handler_dir.name})")
                else:
                    logger.warning(f"⚠️  {module_path} 没有定义 SCHEMA")
            except Exception as e:
                logger.warning(f"⚠️ 加载 Schema 失败 {handler_dir.name}: {e}")
                continue
        
        if self.is_verbose:
            logger.info(f"✅ 共加载 {len(self._schemas)} 个 Schema")
    
    def _load_mapping(self):
        """
        加载 Handler 映射配置（从 userspace 加载）
        
        加载顺序：
        1. 框架默认配置：userspace/data_source/handlers/mapping.json（仅包含 handler 路径和默认 dependencies，作为参考）
        2. 用户配置：userspace/data_source/mapping.json（包含所有可配置内容，会覆盖默认配置）
        
        合并策略：
        - handler: 用户配置可以覆盖框架默认（允许用户切换 handler）
        - dependencies: 用户配置完全覆盖框架默认
        - provider_config, handler_config, is_enabled: 完全由用户配置决定
        """
        # 1. 加载框架默认配置（仅作为参考，从 userspace 加载）
        handlers_path = PathManager.data_source_handlers_mapping()
        default_config = {}
        
        if handlers_path.exists():
            default_data = ConfigManager.load_json(handlers_path)
            default_config = default_data.get("data_sources", {})
            if self.is_verbose:
                logger.debug(f"✅ 加载了框架默认配置: {handlers_path.name}")
        else:
            logger.warning(f"⚠️ 框架默认配置文件不存在: {handlers_path}")
        
        # 2. 加载用户配置（必需）
        user_path = PathManager.data_source_mapping()
        
        if not user_path.exists():
            logger.error(f"❌ 用户配置文件不存在: {user_path}")
            logger.error("   请创建 userspace/data_source/mapping.json 并配置所有 data sources")
            raise FileNotFoundError(f"用户配置文件不存在: {user_path}")
        
        user_config = ConfigManager.load_json(user_path)
        user_data_sources = user_config.get("data_sources", {})
        
        if not user_data_sources:
            logger.warning(f"⚠️ 用户配置文件为空: {user_path}")
        
        # 3. 合并配置：用户配置优先，框架默认作为后备
        merged_config = {}
        
        # 收集所有 data source 名称（来自框架默认和用户配置）
        all_ds_names = set(default_config.keys()) | set(user_data_sources.keys())
        
        for ds_name in all_ds_names:
            default_ds = default_config.get(ds_name, {})
            user_ds = user_data_sources.get(ds_name, {})
            
            # 合并策略：
            # - handler: 用户配置优先，如果没有则使用框架默认
            # - dependencies: 用户配置优先，如果没有则使用框架默认
            # - 其他字段（is_enabled, provider_config, handler_config）: 完全由用户配置决定
            merged_ds = {
                "handler": user_ds.get("handler") or default_ds.get("handler"),
                "dependencies": user_ds.get("dependencies") or default_ds.get("dependencies", {}),
                "is_enabled": user_ds.get("is_enabled", True),  # 默认启用
                "provider_config": user_ds.get("provider_config", {}),
                "handler_config": user_ds.get("handler_config", {}),
            }
            
            # 移除 None 值
            merged_ds = {k: v for k, v in merged_ds.items() if v is not None}
            
            merged_config[ds_name] = merged_ds
        
        if self.is_verbose:
            logger.debug(f"✅ 加载并合并了用户配置: {user_path}（共 {len(merged_config)} 个 data sources）")
        
        # 4. 保存最终合并结果
        self._mapping = merged_config
    
    def _load_definitions(self):
        """
        将配置转换为 DataSourceDefinition 对象
        
        这是必需的步骤，所有配置必须符合新的格式。
        如果配置格式不正确，会记录错误但不会中断加载过程。
        """
        for ds_name, ds_config in self._mapping.items():
            try:
                definition = DataSourceDefinition.from_dict(ds_config, name=ds_name)
                self._definitions[ds_name] = definition
                if self.is_verbose:
                    logger.debug(f"✅ 加载 DataSourceDefinition: {ds_name}")
            except Exception as e:
                logger.error(f"❌ 加载 DataSourceDefinition 失败 {ds_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # 注意：配置格式错误会导致该 Handler 无法加载
    
    def get_definition(self, ds_name: str) -> Optional[DataSourceDefinition]:
        """
        获取 DataSourceDefinition 对象
        
        Args:
            ds_name: 数据源名称
        
        Returns:
            DataSourceDefinition 对象，如果不存在则返回 None
        """
        return self._definitions.get(ds_name)
    
    def _load_handler(self, ds_name: str, handler_path: str):
        """
        动态加载 Handler 类（从 userspace 加载）
        
        Args:
            ds_name: 数据源名称
            handler_path: Handler 类的完整路径（如 "handlers.stock_list.TushareStockListHandler"）
                         现在应该从 userspace 加载，路径格式：userspace.data_source.handlers.xxx
        
        Returns:
            Handler 类
        """
        try:
            # 处理两种路径格式：
            # 1. 旧格式：handlers.stock_list.TushareStockListHandler -> userspace.data_source.handlers.stock_list.TushareStockListHandler
            # 2. 新格式：userspace.data_source.handlers.stock_list.TushareStockListHandler（直接使用）
            if handler_path.startswith("userspace."):
                # 已经是新格式，直接使用
                full_path = handler_path
            elif handler_path.startswith("handlers."):
                # 旧格式，转换为新格式
                full_path = f"userspace.data_source.{handler_path}"
            else:
                # 其他格式，尝试直接导入
                full_path = handler_path
            
            module_path, class_name = full_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            handler_class = getattr(module, class_name)
            if self.is_verbose:
                logger.debug(f"✅ 成功加载 Handler 类: {ds_name} ({full_path})")
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
                # 获取 DataSourceDefinition（必须存在）
                definition = self._definitions.get(ds_name)
                if not definition:
                    logger.error(f"❌ {ds_name} 没有找到 DataSourceDefinition，跳过（配置格式可能不正确）")
                    continue
                
                handler_instance = handler_class(
                    schema, 
                    params={},  # 不再使用 params，所有配置都在 definition 中
                    data_manager=self.data_manager,
                    definition=definition
                )
                
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
