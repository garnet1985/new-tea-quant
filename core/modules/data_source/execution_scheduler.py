# DataSourceExecutionScheduler

# 职责对象：所有enabled & valid 的data sources
# 每个data source的执行：委托每个data source的handler去执行

# 主要工作：
# 按依赖顺序串行执行每个数据源（委托给 handler）
# 在执行时注入依赖数据源的数据到 handler context
# 最后 retry 失败的数据源

from typing import Dict, Any, List, Set, Optional, Tuple
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.data_class.handler_mapping import HandlerMapping
from core.modules.data_source.reserved_dependencies import (
    RESERVED_DEPENDENCY_KEYS,
    resolve_reserved_dependency,
)


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

        self.mappings: Optional[HandlerMapping] = None  # mapping.py 的 DATA_SOURCES

        self._failed_data_sources: List[Tuple[str, BaseHandler, Exception]] = []
        
        self._dependency_cache: Dict[str, Any] = {}

    def run(self, handler_instances: List[BaseHandler], mappings: HandlerMapping):
        """
        执行所有数据源
        
        Args:
            handler_instances: Handler 实例列表
            mappings: HandlerMapping 实例
        """
        self.mappings = mappings
        sorted_handler_instances = self._preprocess(handler_instances)
        self._execute(sorted_handler_instances)
        self._postprocess()


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
        # 拓扑排序 handlers，确定执行顺序
        try:
            topological_sorted_handler_instances = self._topological_sort_handlers(handler_instances)
            return topological_sorted_handler_instances
        except ValueError as e:
            logger.error(f"❌ 数据源依赖关系错误: {e}")
            raise

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
            data_source_key = handler.get_key()
            if data_source_key:
                handler_map[data_source_key] = handler
        
        # 构建依赖图：dep -> [dependent1, dependent2, ...]
        graph = defaultdict(list)
        in_degree = {}
        
        # 初始化 in_degree
        for handler in handlers:
            data_source_key = handler.get_key()
            if data_source_key:
                in_degree[data_source_key] = 0
        
        # 构建图和计算入度
        for handler in handlers:
            data_source_key = handler.get_key()
            if not data_source_key:
                continue
            
            depends_on = handler.get_dependency_data_source_names()
            for dep_name in depends_on:
                if dep_name in RESERVED_DEPENDENCY_KEYS:
                    continue
                if dep_name not in handler_map:
                    raise ValueError(
                        f"数据源 '{data_source_key}' 依赖的数据源 '{dep_name}' 不存在或未启用"
                    )
                graph[dep_name].append(data_source_key)
                in_degree[data_source_key] += 1
        
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
        # 注意：若所有 handler 的 get_key() 均返回非 None（已验证），
        # 那么 len(sorted_handlers) != len(handlers) 表示存在循环依赖
        if len(sorted_handlers) != len(handlers):
            remaining = set(handler_map.keys()) - {h.get_key() for h in sorted_handlers}
            raise ValueError(f"检测到循环依赖或未解析的依赖，剩余数据源: {remaining}")
        
        return sorted_handlers

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
        total = len(sorted_handler_instances)
        logger.info(f"🚀 开始执行 {total} 个数据源")
        
        for idx, handler_instance in enumerate(sorted_handler_instances):
            try:
                data_source_key = handler_instance.get_key()
                logger.info(f"📊 [{idx+1}/{total}] 执行数据源: {data_source_key}")
                dependencies_data = self._get_dependencies_data(data_source_key)
                normalized_data = handler_instance.execute(dependencies_data)
                if self.mappings.is_dependency_for_downstream(data_source_key):
                    self._cache_result(data_source_key, normalized_data)
                logger.info(f"✅ [{idx+1}/{total}] 数据源 {data_source_key} 执行完成")
                # 只在成功执行后才清理不再需要的依赖缓存
                self._clean_up_dependency_cache_if_no_longer_required(sorted_handler_instances, idx)
            except Exception as e:
                self._handle_execution_error(handler_instance, e)

        self._retry_failed_data_sources()
    
    def _get_dependencies_data(self, data_source_key: str) -> Dict[str, Any]:
        """
        收集依赖数据：分两层解析。
        1. 保留依赖（如 latest_trading_date）：由 resolve_reserved_dependency 解析，不来自缓存。
        2. 其他 data source：从 _dependency_cache 取（须先执行过对应 handler）。
        
        Args:
            data_source_key: 数据源配置键（mapping 中的 key）
            
        Returns:
            Dict[str, Any]: 依赖数据字典
        """
        dep = {}
        for dep_name in self.mappings.get_depend_on_data_source_names(data_source_key):
            if dep_name in RESERVED_DEPENDENCY_KEYS:
                dep[dep_name] = resolve_reserved_dependency(dep_name)
            elif dep_name in self._dependency_cache:
                dep[dep_name] = self._dependency_cache[dep_name]
            else:
                raise ValueError(
                    f"数据源 '{data_source_key}' 依赖的 '{dep_name}' 无法解析："
                    f"若为保留依赖请使用 {sorted(RESERVED_DEPENDENCY_KEYS)} 之一，"
                    f"否则须为已执行的 data source 且被缓存。"
                )
        return dep

    def _cache_result(self, data_source_key: str, normalized_data: Dict[str, Any]):
        """
        缓存 handler 执行结果
        
        注意：只缓存那些被其他 data source 依赖的结果，避免内存爆炸
        """
        if normalized_data and "data" in normalized_data:
            self._dependency_cache[data_source_key] = normalized_data["data"]
        elif normalized_data is None:
            logger.warning(f"{data_source_key} 返回结果为 None，缓存不成功")
        elif "data" not in normalized_data:
            logger.warning(f"{data_source_key} 返回结果中缺少 'data' 键，缓存不成功")
        else:
            logger.warning(f"{data_source_key} 返回结果为空，缓存不成功")
    

    def _handle_execution_error(self, handler_instance: BaseHandler, error: Exception):
        """
        处理执行错误
        
        注意：handler_instance.get_key() 不会返回 None（已验证），因此不需要检查
        """
        data_source_key = handler_instance.get_key()
        logger.error(f"❌ 数据源 {data_source_key} 执行失败: {error}")
        self._failed_data_sources.append((data_source_key, handler_instance, error))

    def _retry_failed_data_sources(self):
        """
        重试失败的数据源。
        
        步骤：
        1. 遍历所有失败的数据源
        2. 对每个失败的 handler：获取依赖数据 → 执行 → 缓存结果
        3. 如果重试仍然失败，记录到新的失败列表
        4. 更新失败列表
        """
        if not self._failed_data_sources:
            return
        
        logger.info(f"🔄 开始重试 {len(self._failed_data_sources)} 个失败的数据源")
        retry_failed = []
        
        for data_source_key, handler_instance, _ in self._failed_data_sources:
            try:
                # 获取依赖数据（如果依赖也失败了，这里可能会抛出异常）
                dependencies_data = self._get_dependencies_data(data_source_key)
                
                # 执行 handler
                normalized_data = handler_instance.execute(dependencies_data)
                
                # 如果需要缓存，则缓存结果
                # 注意：self.mappings 在 run() 方法中已赋值，不会是 None
                if self.mappings.is_dependency_for_downstream(data_source_key):
                    self._cache_result(data_source_key, normalized_data)
                
                logger.info(f"✅ 数据源 {data_source_key} 重试成功")
            except ValueError as e:
                # 依赖数据缺失的情况
                logger.warning(f"⚠️  数据源 {data_source_key} 重试失败：依赖数据缺失 - {e}")
                retry_failed.append((data_source_key, handler_instance, e))
            except Exception as e:
                # 其他执行错误
                logger.error(f"❌ 数据源 {data_source_key} 重试仍然失败: {e}")
                retry_failed.append((data_source_key, handler_instance, e))
        
        # 更新失败列表
        self._failed_data_sources = retry_failed
        if retry_failed:
            logger.warning(f"⚠️  仍有 {len(retry_failed)} 个数据源重试失败")

    def _clean_up_dependency_cache_if_no_longer_required(self, sorted_handler_instances: List[BaseHandler], idx: int):
        """
        检查依赖是否仍然需要，清理不再需要的依赖缓存。
        
        在每次 data source 任务完成后调用，用于减少内存使用。
        
        步骤：
        1. 检查剩余的未完成任务是否还需要某个依赖
        2. 检查重试任务是否还需要某个依赖
        3. 如果某个依赖不再被需要，清理该依赖的缓存
        
        Args:
            sorted_handler_instances: 已排序的 Handler 列表
            idx: 当前执行到的 Handler 索引
        """
 
        remaining_tasks = sorted_handler_instances[idx + 1:]

        # 收集所有仍需要的依赖名称
        required_dependencies: Set[str] = set()
        
        # 1. 检查剩余未完成任务需要的依赖
        for handler in remaining_tasks:
            depends_on = handler.get_dependency_data_source_names()
            required_dependencies.update(depends_on)
        
        # 2. 检查重试任务需要的依赖
        for _, handler_instance, _ in self._failed_data_sources:
            depends_on = handler_instance.get_dependency_data_source_names()
            required_dependencies.update(depends_on)
        
        # 3. 清理不再需要的依赖缓存
        cached_dependencies = set(self._dependency_cache.keys())
        dependencies_to_remove = cached_dependencies - required_dependencies
        
        for dep_name in dependencies_to_remove:
            del self._dependency_cache[dep_name]
            if self.is_verbose:
                logger.debug(f"🗑️  清理不再需要的依赖缓存: {dep_name}")

    # ================================
    # postprocess stage
    # ================================
    def _postprocess(self):
        self._clear_cache()

    def _clear_cache(self):
        """
        清理缓存和失败列表。
        
        在 postprocess 阶段调用，清理所有执行过程中产生的缓存数据和失败记录。
        """
        self._dependency_cache.clear()
        self._failed_data_sources.clear()