# DataSourceExecutionScheduler

# 职责对象：所有enabled & valid 的data sources
# 每个data source的执行：委托每个data source的handler去执行

# 主要工作：
# 按依赖顺序串行执行每个数据源（委托给 handler）
# 在执行时注入依赖数据源的数据到 handler context
# 最后 retry 失败的数据源

from typing import Dict, Any, List, Set, Optional
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_manager.data_manager import DataManager


class DataSourceExecutionScheduler:
    """
    DataSourceExecutionScheduler: 数据源执行调度器。
    
    职责：
    - 按依赖顺序串行执行每个数据源（委托给 handler）
    - 在执行时注入依赖数据源的数据到 handler context
    - 最后 retry 失败的数据源
    """
    
    def __init__(self, is_verbose: bool = False):
        """
        初始化调度器
        
        Args:
            is_verbose: 是否显示详细日志
        """
        self.is_verbose = is_verbose
        self._failed_data_sources = []  # [(handler_name, error), ...]
        self._data_manager = DataManager.get_instance()
        self._executed_data_sources: Dict[str, Any] = {}  # 缓存已执行的数据源数据
        self._mappings: Dict[str, Dict[str, Any]] = {}  # mapping.json 的内容
        
        self._dependency_names: Set[str] = set()  # 被其他数据源依赖的数据源集合
        self._dependency_cache: Dict[str, Any] = {}  # 依赖数据缓存

    def run(self, handler_instances: List[BaseHandler], mappings: Dict[str, Dict[str, Any]] = None):
        """
        执行所有数据源
        
        Args:
            handler_instances: Handler 实例列表
            mappings: mapping.json 的内容（用于获取 depends_on 信息），如果为 None 则自动加载
        """
        self._mappings = mappings
        sorted_handler_instances = self._preprocess(handler_instances)
        self._execute(sorted_handler_instances)
        self._postprocess()

    def _get_handler_data_source_dependencies(self, handler: BaseHandler) -> List[str]:
        """
        获取指定 handler 依赖的数据源列表。
        
        Args:
            handler: Handler 实例
            
        Returns:
            List[str]: 该 handler 依赖的数据源名称列表
        """
        data_source_name = handler.context.get("data_source_name")
        if not data_source_name:
            return []
        
        # 从 mapping.json 中获取该 handler 的数据源依赖声明
        data_source_config = self._mappings.get(data_source_name, {})
        depends_on = data_source_config.get("depends_on", [])
        
        if isinstance(depends_on, list):
            return depends_on
        return []
    
    def _load_dependency_data(self, data_source_name: str) -> Any:
        """
        从数据库加载依赖数据源的数据（备用方法，用于特殊情况）。
        
        注意：正常情况下，依赖数据应该从 execute() 的返回值缓存中获取。
        此方法仅用于特殊情况（如重试时可能需要从数据库加载）。
        
        统一策略：尝试从数据库表加载数据
        - 如果表存在，加载所有数据
        - 如果表不存在或加载失败，返回 None
        
        Args:
            data_source_name: 数据源名称
            
        Returns:
            Any: 依赖数据源的数据，如果无法加载则返回 None
        """
        try:
            # 统一处理：尝试从表读取数据
            table = self._data_manager.get_table(data_source_name)
            if table:
                return table.load("1=1")
            
            logger.warning(f"⚠️ 无法找到数据源 '{data_source_name}' 对应的表，依赖数据将不可用")
            return None
        except Exception as e:
            logger.warning(f"⚠️ 加载依赖数据源 '{data_source_name}' 的数据失败: {e}")
            return None
    
    def _topological_sort_handlers(self, handlers: List[BaseHandler]) -> List[BaseHandler]:
        """
        对 handlers 进行拓扑排序，确保依赖的数据源先执行。
        
        Args:
            handlers: Handler 列表
            
        Returns:
            List[BaseHandler]: 排序后的 Handler 列表
            
        Raises:
            ValueError: 如果存在循环依赖或依赖的数据源不存在
        """
        from collections import defaultdict, deque
        
        # 构建 handler 名称到 handler 的映射
        handler_map = {}
        for handler in handlers:
            data_source_name = handler.context.get("data_source_name")
            if data_source_name:
                handler_map[data_source_name] = handler
        
        # 构建依赖图：dep -> [dependent1, dependent2, ...]
        graph = defaultdict(list)
        in_degree = {}
        
        # 初始化 in_degree
        for handler in handlers:
            data_source_name = handler.context.get("data_source_name")
            if data_source_name:
                in_degree[data_source_name] = 0
        
        # 构建图和计算入度
        for handler in handlers:
            data_source_name = handler.context.get("data_source_name")
            if not data_source_name:
                continue
            
            depends_on = self._get_handler_data_source_dependencies(handler)
            for dep_name in depends_on:
                if dep_name not in handler_map:
                    raise ValueError(
                        f"数据源 '{data_source_name}' 依赖的数据源 '{dep_name}' 不存在或未启用"
                    )
                graph[dep_name].append(data_source_name)
                in_degree[data_source_name] = in_degree.get(data_source_name, 0) + 1
                # 记录被依赖的数据源（需要缓存结果）
                self._dependency_names.add(dep_name)
        
        # 拓扑排序
        sorted_handlers = []
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        
        while queue:
            current_name = queue.popleft()
            sorted_handlers.append(handler_map[current_name])
            
            # 更新依赖当前 handler 的其他 handlers 的入度
            for dependent_name in graph[current_name]:
                in_degree[dependent_name] -= 1
                if in_degree[dependent_name] == 0:
                    queue.append(dependent_name)
        
        # 检查是否存在循环依赖
        if len(sorted_handlers) != len(handlers):
            remaining = set(handler_map.keys()) - {h.context.get("data_source_name") for h in sorted_handlers}
            raise ValueError(f"检测到循环依赖或未解析的依赖，剩余数据源: {remaining}")
        
        return sorted_handlers

    # ================================
    # preprocess stage
    # ================================

    def _preprocess(self, handler_instances: List[BaseHandler]):
        """
        预处理阶段：拓扑排序 handlers，确定执行顺序。
        
        注意：
        - 不在这里加载依赖数据，因为依赖的 handler 可能还没执行
        - 依赖数据的注入在 _execute 阶段进行，直接从 execute() 的返回值缓存中获取
        - 同时记录哪些 data source 被其他 data source 依赖（用于决定是否缓存结果）
        """
        # 清空依赖集合（每次执行前重置）
        self._dependency_names.clear()
        
        # 拓扑排序 handlers，确定执行顺序
        try:
            topological_sorted_handler_instances = self._topological_sort_handlers(handler_instances)
            return topological_sorted_handler_instances
        except ValueError as e:
            logger.error(f"❌ 数据源依赖关系错误: {e}")
            raise


    # ================================
    # execute stage
    # ================================

    def _execute(self, sorted_handler_instances: List[BaseHandler]):
        """
        执行阶段：按依赖顺序执行所有数据源。
        
        步骤：
        1. 遍历排序后的 handlers（已在 preprocess 中排序）
        2. 对于每个 handler：注入依赖数据 → 执行 → 缓存结果
        3. 捕获异常并记录失败的 handler
        4. 最后重试失败的 handler
        """
        for handler_instance in sorted_handler_instances:
            try:
                data_source_name = handler_instance.context.get("data_source_name")
                dependency_names = handler_instance.get_dependency_names()
                dependencies = self._gather_dependencies(dependency_names)
                normalized_data = handler_instance.execute(dependencies)
                if self._is_dependency(data_source_name):
                    self._cache_result(data_source_name, normalized_data)
                self._check_if_dependency_still_required(sorted_handler_instances)
            except Exception as e:
                self._handle_execution_error(handler_instance, e)

        self._retry_failed_data_sources()
    
    def _gather_dependencies(self, dependency_names: List[str]) -> Dict[str, Any]:
        """
        收集依赖数据
        
        注意：返回深拷贝，避免修改影响缓存中的数据
        
        Args:
            dependency_names: 依赖数据源名称列表
            
        Returns:
            Dict[str, Any]: 依赖数据字典（深拷贝）
        """
        dep = {}
        for dep_name in dependency_names:
            if dep_name in self._dependency_cache:
                dep[dep_name] = self._dependency_cache[dep_name]
        return dep

    def _is_dependency(self, data_source_name: str) -> bool:
        """检查是否是依赖数据源"""
        return data_source_name in self._dependency_names

    def _cache_result(self, data_source_name: str, normalized_data: Dict[str, Any]):
        """
        缓存 handler 执行结果
        
        注意：只缓存那些被其他 data source 依赖的结果，避免内存爆炸
        """
        self._dependency_cache[data_source_name] = normalized_data
    

    def _handle_execution_error(self, handler_instance: BaseHandler, error: Exception):
        """处理执行错误"""
        data_source_name = handler_instance.context.get("data_source_name", "unknown")
        logger.error(f"❌ 数据源 {data_source_name} 执行失败: {error}")
        self._failed_data_sources.append((data_source_name, handler_instance, error))

    def _retry_failed_data_sources(self):
        """重试失败的数据源"""
        if not self._failed_data_sources:
            return
        
        logger.info(f"🔄 开始重试 {len(self._failed_data_sources)} 个失败的数据源")
        retry_failed = []
        
        for data_source_name, handler_instance, error in self._failed_data_sources:
            try:
                self._inject_dependencies(handler_instance)
                normalized_data = handler_instance.execute({})
                self._cache_result(handler_instance, normalized_data)
                logger.info(f"✅ 数据源 {data_source_name} 重试成功")
            except Exception as e:
                logger.error(f"❌ 数据源 {data_source_name} 重试仍然失败: {e}")
                retry_failed.append((data_source_name, handler_instance, e))
        
        self._failed_data_sources = retry_failed
        if retry_failed:
            logger.warning(f"⚠️ 仍有 {len(retry_failed)} 个数据源重试失败")

    def _check_if_dependency_still_required(self, remaining_tasks: List[BaseHandler]) -> bool:
        """检查依赖是否仍然需要"""
        # todo: to be implemented to reduce memory usage as soon as possible
        # will be called after each data source task is completed
        # 1. check rest of unfinished data sources if they require any dependency in the list
        # 2. check the retry work if they require any dependency in the list
        # 3. if no dependency required, clear the dependency cache of that one data source
        pass

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
        self._dependency_cache.clear()
        self._failed_data_sources.clear()
        self._dependency_names.clear()