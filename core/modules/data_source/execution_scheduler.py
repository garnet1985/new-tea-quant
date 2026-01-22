# DataSourceExecutionScheduler

# 职责对象：所有enabled & valid 的data sources
# 每个data source的执行：委托每个data source的handler去执行

# 主要工作：
# 准备全局依赖（解析、获取、缓存）
# 按依赖顺序串行执行每个数据源（委托给 handler）
# 提供必要的上下文数据（注入到 handler context）
# 最后 retry 失败的数据源

from typing import Dict, Any, List, Set
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_manager.data_manager import DataManager


class DataSourceExecutionScheduler:
    """
    DataSourceExecutionScheduler: 数据源执行调度器。

    职责：
    - 准备全局依赖（解析、获取、缓存）
    - 按依赖顺序串行执行每个数据源（委托给 handler）
    - 提供必要的上下文数据（注入到 handler context）
    - 最后 retry 失败的数据源
    """
    
    # 全局依赖获取器注册表（可扩展）
    _DEPENDENCY_FETCHERS = {
        "latest_completed_trading_date": lambda dm: dm.service.calendar.get_latest_completed_trading_date(),
        "stock_list": lambda dm: dm.stock.list.load(filtered=True),
        # 未来可以添加：
        # "market_status": lambda dm: dm.get_market_status(),
        # "trading_calendar": lambda dm: dm.get_trading_calendar(),
    }
    
    def __init__(self, data_source_manager):
        """
        初始化调度器
        
        Args:
            data_source_manager: DataSourceManager 实例，用于获取 handlers 和 mappings
        """
        self.data_source_manager = data_source_manager
        self._failed_data_sources = []  # [(handler_name, error), ...]
        self._global_dependencies: Dict[str, Any] = {}  # 缓存的全局依赖
        self._handlers: List[BaseHandler] = []  # 所有启用的 handlers
        self._data_manager = DataManager.get_instance()

    def run(self, handlers: List[BaseHandler], required_global_deps: Set[str]):
        """执行所有数据源"""
        self._handlers = handlers
        self._preprocess(required_global_deps)
        self._execute()
        self._postprocess()

    # ================================
    # preprocess stage
    # ================================
    def _preprocess(self, required_global_deps: Set[str]):
        """
        预处理阶段：获取并缓存全局依赖。
        
        步骤：
        1. 根据已收集的依赖需求，集中请求全局数据
        2. 将获取到的全局依赖缓存在内存中，供后续执行阶段使用
        
        注意：依赖需求已在 DataSourceManager 中收集完成，这里只需要获取和缓存。
        """
        self._global_dependencies = self._fetch_global_dependencies(required_global_deps)
        logger.info(f"✅ 预处理完成：获取了 {len(self._global_dependencies)} 个全局依赖")

    def _fetch_global_dependencies(self, dep_names: Set[str]) -> Dict[str, Any]:
        """
        集中请求全局需要的数据并缓存在内存。
        
        步骤：
        1. 总是自动获取 latest_completed_trading_date（很多 handler 都需要）
        2. 获取其他声明的依赖
        3. 返回包含所有全局依赖的字典
        
        Args:
            dep_names: 需要获取的依赖名称集合
            
        Returns:
            Dict[str, Any]: 包含所有全局依赖的字典（缓存在内存中）
        """
        shared_context = {}
        
        # 步骤 1：总是自动获取 latest_completed_trading_date，因为很多 handler 都需要它
        # 即使没有 handler 声明依赖，也应该提供（避免警告）
        if "latest_completed_trading_date" in self._DEPENDENCY_FETCHERS:
            try:
                fetcher = self._DEPENDENCY_FETCHERS["latest_completed_trading_date"]
                value = fetcher(self._data_manager)
                shared_context["latest_completed_trading_date"] = value
            except Exception as e:
                logger.warning(f"⚠️ 获取 latest_completed_trading_date 失败: {e}，handler 将回退获取")
        
        # 步骤 2：获取其他声明的依赖
        for dep_name in dep_names:
            # 跳过 latest_completed_trading_date，因为已经在上面处理了
            if dep_name == "latest_completed_trading_date":
                continue
                
            if dep_name in self._DEPENDENCY_FETCHERS:
                try:
                    fetcher = self._DEPENDENCY_FETCHERS[dep_name]
                    value = fetcher(self._data_manager)
                    shared_context[dep_name] = value
                except Exception as e:
                    logger.error(f"❌ 获取全局依赖失败 {dep_name}: {e}")
            else:
                logger.warning(f"⚠️ 未知的全局依赖: {dep_name}（可能未在 _DEPENDENCY_FETCHERS 中注册）")
        
        return shared_context

    def _get_handler_required_dependencies(self, handler: BaseHandler) -> Set[str]:
        """
        获取指定 handler 需要的全局依赖。
        
        Args:
            handler: Handler 实例
            
        Returns:
            Set[str]: 该 handler 需要的依赖名称集合
        """
        data_source_name = handler.context.get("data_source_name")
        if not data_source_name:
            return set()
        
        # 从 mapping.json 中获取该 handler 的依赖声明
        mappings = self.data_source_manager.mappings
        data_source_config = mappings.get(data_source_name, {})
        dependencies = data_source_config.get("dependencies", {})
        
        required_deps = set()
        if isinstance(dependencies, dict):
            for dep_name, required in dependencies.items():
                if required:
                    required_deps.add(dep_name)
        
        return required_deps

    # ================================
    # execute stage
    # ================================

    def _execute(self):
        """
        执行阶段：按顺序执行所有数据源。
        
        步骤：
        1. 遍历所有 handlers，为每个 handler 准备其需要的全局依赖
        2. 调用 handler.execute() 执行数据获取
        3. 捕获异常并记录失败的 handler
        4. 最后重试失败的 handler
        """
        for handler in self._handlers:
            try:
                # 获取该 handler 需要的依赖
                required_deps = self._get_handler_required_dependencies(handler)
                handler_dependencies = {k: v for k, v in self._global_dependencies.items() if k in required_deps}
                handler.execute(handler_dependencies)
            except Exception as e:
                data_source_name = handler.context.get("data_source_name", "unknown")
                logger.error(f"❌ 数据源 {data_source_name} 执行失败: {e}")
                self._failed_data_sources.append((data_source_name, handler, e))

        logger.info(f"✅ 所有数据源执行完成，失败 {len(self._failed_data_sources)} 个，开始重试")
        self._retry_failed_data_sources()

    def _retry_failed_data_sources(self):
        """
        重试失败的数据源。
        
        注意：如果是因为限流原因导致失败，可能需要等待一段时间再重试。
        """
        if not self._failed_data_sources:
            return
        
        logger.info(f"🔄 开始重试 {len(self._failed_data_sources)} 个失败的数据源")
        retry_failed = []
        
        for data_source_name, handler, error in self._failed_data_sources:
            try:
                # 获取该 handler 需要的依赖并重新执行
                required_deps = self._get_handler_required_dependencies(handler)
                handler_dependencies = {k: v for k, v in self._global_dependencies.items() if k in required_deps}
                handler.execute(handler_dependencies)
                logger.info(f"✅ 数据源 {data_source_name} 重试成功")
            except Exception as e:
                logger.error(f"❌ 数据源 {data_source_name} 重试仍然失败: {e}")
                retry_failed.append((data_source_name, handler, e))
        
        self._failed_data_sources = retry_failed
        if retry_failed:
            logger.warning(f"⚠️ 仍有 {len(retry_failed)} 个数据源重试失败")

    # ================================
    # postprocess stage
    # ================================
    def _postprocess(self):
        self._clear_cache()

    def _clear_cache(self):
        """
        清理缓存。
        
        注意：handlers 是外部传入的，不应该在这里清空。
        """
        self._global_dependencies.clear()
        self._failed_data_sources.clear()