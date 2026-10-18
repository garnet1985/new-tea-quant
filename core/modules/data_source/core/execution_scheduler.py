from core.infra.cmd_layout import i

# DataSourceExecutionScheduler

# 职责对象：所有enabled & valid 的data sources
# 每个data source的执行：委托每个data source的handler去执行

# 主要工作：
# 按依赖顺序串行执行每个数据源（委托给 handler）
# 在执行时注入依赖数据源的数据到 handler context
# 最后 retry 失败的数据源

from typing import Dict, Any, List, Set, Optional, Tuple
import logging
import time

from core.modules.data_source.core.base_class.base_handler import BaseHandler, format_run_seconds
from core.infra.progress import Progress
from core.modules.data_source.core.progress import bind_renew_leaf
from core.modules.data_source.core.service.run_status import (
    RunStatus,
    call_with_status,
    ordered_source_keys,
)
from core.modules.data_source.core.data_class.handler_mapping import HandlerMapping
from core.modules.data_source.core.reserved_dependencies import (
    RESERVED_DEPENDENCY_KEYS,
    resolve_reserved_dependency,
)


logger = logging.getLogger(__name__)


def _safe_id(value: str) -> str:
    return str(value or "").replace("/", "-").replace("\\", "-").replace("\x00", "")


def _progress_root_id(progress_id: Optional[str]) -> str:
    cleaned = _safe_id(progress_id or "")
    if cleaned and cleaned not in {".", ".."}:
        return cleaned
    return f"renew-{time.strftime('%Y%m%dT%H%M%S')}"


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
        self._progress_root = ""
        self._progress_nodes: Dict[str, str] = {}

    def run(
        self,
        handler_instances: List[BaseHandler],
        mappings: HandlerMapping,
        *,
        force: bool = False,
        progress_id: Optional[str] = None,
    ):
        """
        执行所有数据源
        
        Args:
            handler_instances: Handler 实例列表
            mappings: HandlerMapping 实例
            force: 强制全量重拉（忽略 last_update / stock_list 日缓存等）
        """
        self.mappings = mappings
        self._force_refresh = bool(force)
        self._progress_id = progress_id
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
            logger.error(f"{i('error')} 数据源依赖关系错误: {e}")
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
        handler_map = {}
        enabled: Dict[str, Any] = {}
        for handler in handlers:
            data_source_key = handler.get_key()
            if not data_source_key:
                continue
            handler_map[data_source_key] = handler
            info: Dict[str, Any] = {
                "depends_on": handler.get_dependency_data_source_names(),
            }
            if self.mappings is not None:
                raw = self.mappings.data_sources.get(data_source_key) or {}
                if "weight" in raw:
                    info["weight"] = raw.get("weight")
            enabled[data_source_key] = info

        for data_source_key, info in enabled.items():
            for dep_name in info["depends_on"]:
                if dep_name in RESERVED_DEPENDENCY_KEYS:
                    continue
                if dep_name not in handler_map:
                    raise ValueError(
                        f"数据源 '{data_source_key}' 依赖的数据源 '{dep_name}' 不存在或未启用"
                    )

        ordered = ordered_source_keys(enabled)
        return [handler_map[name] for name in ordered]

    def open_progress(self, handlers: List[BaseHandler], progress_id: Optional[str] = None) -> None:
        """每个数据源一层。根 id 用这次任务的 id，没有就按时间生成。"""
        root = _progress_root_id(progress_id)
        steps = []
        nodes: Dict[str, str] = {}
        for handler in handlers:
            key = str(handler.get_key() or "")
            if not key or key in nodes:
                continue
            node_id = f"{root}:{_safe_id(key)}"
            nodes[key] = node_id
            steps.append({"id": node_id, "label": key})
        self._progress_nodes = nodes
        if not steps:
            self._progress_root = ""
            return
        Progress.start(root, job="renew", label="更新数据", steps=steps)
        self._progress_root = root

    def begin_source(self, key: str) -> None:
        node_id = self._progress_nodes.get(key, "")
        if not node_id:
            bind_renew_leaf("")
            return
        bind_renew_leaf(node_id)
        Progress.tick(node_id, 0, 1, source=key, log=False)

    def finish_source(self, key: str) -> None:
        node_id = self._progress_nodes.get(key, "")
        bind_renew_leaf("")
        if node_id:
            Progress.finish(node_id)

    def fail_source(self, key: str, error: BaseException) -> None:
        node_id = self._progress_nodes.get(key, "")
        bind_renew_leaf("")
        if not node_id:
            return
        message = str(error).splitlines()[0] if str(error) else ""
        Progress.fail(node_id, detail=message)

    def close_progress(self) -> None:
        bind_renew_leaf("")
        root = self._progress_root
        self._progress_root = ""
        if root:
            Progress.finish(root)

    def fail_progress(self, error: Optional[BaseException] = None) -> None:
        bind_renew_leaf("")
        root = self._progress_root
        self._progress_root = ""
        if not root:
            return
        message = ""
        if error is not None and str(error):
            message = str(error).splitlines()[0]
        Progress.fail(root, detail=message)

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
        self._run_status = RunStatus.open(
            sorted_handler_instances,
            force=getattr(self, "_force_refresh", False),
        )
        self.open_progress(sorted_handler_instances, getattr(self, "_progress_id", None))
        print(f"{i('rocket')} 开始执行 {total} 个数据源", flush=True)
        logger.info("开始执行 %s 个数据源", total)

        try:
            self._run_sources(sorted_handler_instances)
            self.close_progress()
        except Exception as exc:
            self.fail_progress(exc)
            raise

    def _run_sources(self, sorted_handler_instances: List[BaseHandler]) -> None:
        total = len(sorted_handler_instances)
        for idx, handler_instance in enumerate(sorted_handler_instances):
            data_source_key = handler_instance.get_key()
            self.begin_source(data_source_key)
            started = time.perf_counter()
            try:
                mode = handler_instance.renew_mode_label(
                    force=getattr(self, "_force_refresh", False)
                )
                print(
                    f"{i('bar_chart')} [{idx+1}/{total}] 执行数据源: {data_source_key} - 执行模式：{mode}",
                    flush=True,
                )
                logger.info(
                    "执行数据源 [%s/%s]: %s 执行模式：%s",
                    idx + 1,
                    total,
                    data_source_key,
                    mode,
                )
                handler_instance.context["retain_results"] = (
                    self.mappings.is_dependency_for_downstream(data_source_key)
                )
                dependencies_data = self._get_dependencies_data(data_source_key)
                if getattr(self, "_force_refresh", False):
                    dependencies_data = dict(dependencies_data or {})
                    dependencies_data["_execution"] = {"force_refresh": True}
                normalized_data = call_with_status(
                    self._run_status,
                    handler_instance,
                    lambda handler=handler_instance, deps=dependencies_data: handler.execute(deps),
                )
                if self.mappings.is_dependency_for_downstream(data_source_key):
                    self._cache_result(data_source_key, normalized_data)
                total_s = time.perf_counter() - started
                execute_s = self._execute_seconds(handler_instance, total_s)
                print(
                    f"{i('success')} [{idx+1}/{total}] 数据源 {data_source_key} 执行完成，"
                    f"执行耗时：{format_run_seconds(execute_s)}，总任务耗时：{format_run_seconds(total_s)}",
                    flush=True,
                )
                logger.info(
                    "数据源 %s 执行完成，执行耗时：%s，总任务耗时：%s",
                    data_source_key,
                    format_run_seconds(execute_s),
                    format_run_seconds(total_s),
                )
                # 只在成功执行后才清理不再需要的依赖缓存
                self._clean_up_dependency_cache_if_no_longer_required(sorted_handler_instances, idx)
                self.finish_source(data_source_key)
            except Exception as e:
                total_s = time.perf_counter() - started
                self.fail_source(data_source_key, e)
                self._handle_execution_error(handler_instance, e, elapsed=total_s)

        self._retry_failed_data_sources()
    
    def _get_dependencies_data(self, data_source_key: str) -> Dict[str, Any]:
        """
        收集依赖数据：分两层解析。
        1. 保留依赖（如 latest_completed_trading_date）：由 resolve_reserved_dependency 解析，不来自缓存。
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
    

    def _execute_seconds(self, handler_instance: BaseHandler, total_s: float) -> float:
        timing = getattr(handler_instance, "_last_run_timing", None) or {}
        execute_s = timing.get("execute")
        if execute_s is None:
            return total_s
        return float(execute_s)

    def _handle_execution_error(
        self,
        handler_instance: BaseHandler,
        error: Exception,
        *,
        elapsed: float = 0.0,
    ):
        """
        处理执行错误
        
        注意：handler_instance.get_key() 不会返回 None（已验证），因此不需要检查
        """
        data_source_key = handler_instance.get_key()
        spent = format_run_seconds(elapsed)
        print(
            f"{i('error')} 数据源 {data_source_key} 执行失败: {error}，总任务耗时：{spent}",
            flush=True,
        )
        logger.info("数据源 %s 执行失败: %s，总任务耗时：%s", data_source_key, error, spent)
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
        
        n_failed = len(self._failed_data_sources)
        print(f"{i('ongoing')} 开始重试 {n_failed} 个失败的数据源", flush=True)
        logger.info("开始重试 %s 个失败的数据源", n_failed)
        retry_failed = []

        for data_source_key, handler_instance, _ in self._failed_data_sources:
            self.begin_source(data_source_key)
            started = time.perf_counter()
            try:
                # 获取依赖数据（如果依赖也失败了，这里可能会抛出异常）
                dependencies_data = self._get_dependencies_data(data_source_key)
                
                # 执行 handler
                normalized_data = call_with_status(
                    self._run_status,
                    handler_instance,
                    lambda handler=handler_instance, deps=dependencies_data: handler.execute(deps),
                )
                
                # 如果需要缓存，则缓存结果
                # 注意：self.mappings 在 run() 方法中已赋值，不会是 None
                if self.mappings.is_dependency_for_downstream(data_source_key):
                    self._cache_result(data_source_key, normalized_data)
                
                total_s = time.perf_counter() - started
                execute_s = self._execute_seconds(handler_instance, total_s)
                print(
                    f"{i('success')} 数据源 {data_source_key} 重试成功，"
                    f"执行耗时：{format_run_seconds(execute_s)}，总任务耗时：{format_run_seconds(total_s)}",
                    flush=True,
                )
                logger.info(
                    "数据源 %s 重试成功，执行耗时：%s，总任务耗时：%s",
                    data_source_key,
                    format_run_seconds(execute_s),
                    format_run_seconds(total_s),
                )
                self.finish_source(data_source_key)
            except ValueError as e:
                total_s = time.perf_counter() - started
                self.fail_source(data_source_key, e)
                print(
                    f"{i('warning')}  数据源 {data_source_key} 重试失败：依赖数据缺失 - {e}，"
                    f"总任务耗时：{format_run_seconds(total_s)}",
                    flush=True,
                )
                logger.info(
                    "数据源 %s 重试失败：依赖数据缺失 - %s，总任务耗时：%s",
                    data_source_key,
                    e,
                    format_run_seconds(total_s),
                )
                retry_failed.append((data_source_key, handler_instance, e))
            except Exception as e:
                total_s = time.perf_counter() - started
                self.fail_source(data_source_key, e)
                print(
                    f"{i('error')} 数据源 {data_source_key} 重试仍然失败: {e}，"
                    f"总任务耗时：{format_run_seconds(total_s)}",
                    flush=True,
                )
                logger.info(
                    "数据源 %s 重试仍然失败: %s，总任务耗时：%s",
                    data_source_key,
                    e,
                    format_run_seconds(total_s),
                )
                retry_failed.append((data_source_key, handler_instance, e))
        
        # 更新失败列表
        self._failed_data_sources = retry_failed
        if retry_failed:
            print(
                f"{i('warning')}  仍有 {len(retry_failed)} 个数据源重试失败",
                flush=True,
            )
            logger.info("仍有 %s 个数据源重试失败", len(retry_failed))

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
                logger.debug(f"{i('trash')}  清理不再需要的依赖缓存: {dep_name}")

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