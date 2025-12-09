"""
API 执行计划系统

设计思路：
1. 通过配置定义 API 调用计划（铺平的 API 数组）
2. 解析配置得到执行计划（拓扑排序）
3. 生成 Job 列表
4. 根据 Job 数量决定是否多线程
5. 根据并行/串行决定限流策略
6. 执行并获取数据
"""
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque
from loguru import logger
from dataclasses import dataclass


@dataclass
class APIJob:
    """单个 API 调用任务"""
    api_name: str                    # API 名称（用于依赖关系）
    provider_name: str               # Provider 名称
    method: str                      # Provider 方法名
    params: Dict[str, Any]           # 调用参数
    depends_on: List[str]           # 依赖的 API 名称列表（用于拓扑排序）
    batch_by: Optional[str] = None   # 批量处理字段（如 "stock_code"）
    merge_strategy: Optional[str] = None  # 合并策略（如 "left_join"）


@dataclass
class ExecutionStage:
    """执行阶段（拓扑排序后的一个层级）"""
    stage_id: int                    # 阶段编号（0, 1, 2...）
    apis: List[APIJob]                # 该阶段可以并行执行的 API
    # 注意：同一阶段的 API 总是可以并行执行（因为它们没有依赖关系）


@dataclass
class ExecutionPlan:
    """完整的执行计划"""
    stages: List[ExecutionStage]      # 执行阶段列表（按顺序执行）
    providers: Set[str]               # 需要的 Provider 列表
    total_jobs: int                  # 总 Job 数量（展开后）


@dataclass
class ExpandedJob:
    """展开后的 Job（用于实际执行）"""
    api_name: str                    # API 名称
    provider_name: str               # Provider 名称
    method: str                      # Provider 方法名
    params: Dict[str, Any]           # 调用参数（已展开）
    stage_id: int                    # 所属阶段
    depends_on_results: List[str]    # 依赖的前置 API 结果（用于合并）


class JobExpander:
    """Job 展开器：将 API 配置展开为多个执行 Job"""
    
    def __init__(self, execution_plan: ExecutionPlan, context: Dict[str, Any]):
        """
        初始化 Job 展开器
        
        Args:
            execution_plan: 执行计划
            context: 执行上下文，包含：
                - stock_codes: 股票代码列表（如果 batch_by="stock_code"）
                - start_date: 开始日期
                - end_date: 结束日期
                - ... 其他上下文信息
        """
        self.execution_plan = execution_plan
        self.context = context
    
    def expand(self) -> Dict[int, List[ExpandedJob]]:
        """
        展开执行计划为具体的 Job 列表
        
        Returns:
            Dict[int, List[ExpandedJob]]: {stage_id: [job1, job2, ...]}
        """
        expanded_jobs = {}
        
        for stage in self.execution_plan.stages:
            stage_jobs = []
            
            for api_job in stage.apis:
                # 展开单个 API Job
                jobs = self._expand_single_api(api_job, stage.stage_id)
                stage_jobs.extend(jobs)
            
            expanded_jobs[stage.stage_id] = stage_jobs
        
        return expanded_jobs
    
    def _expand_single_api(self, api_job: APIJob, stage_id: int) -> List[ExpandedJob]:
        """
        展开单个 API Job
        
        如果 batch_by 不为空，则根据该字段展开为多个 Job
        """
        # 如果没有 batch_by，直接返回一个 Job
        if not api_job.batch_by:
            return [ExpandedJob(
                api_name=api_job.api_name,
                provider_name=api_job.provider_name,
                method=api_job.method,
                params=self._resolve_params(api_job.params),
                stage_id=stage_id,
                depends_on_results=api_job.depends_on,
            )]
        
        # 根据 batch_by 字段展开
        batch_values = self._get_batch_values(api_job.batch_by)
        
        jobs = []
        for batch_value in batch_values:
            # 为每个 batch_value 创建一个 Job
            params = self._resolve_params(api_job.params, batch_value, api_job.batch_by)
            
            job = ExpandedJob(
                api_name=api_job.api_name,
                provider_name=api_job.provider_name,
                method=api_job.method,
                params=params,
                stage_id=stage_id,
                depends_on_results=api_job.depends_on,
            )
            jobs.append(job)
        
        return jobs
    
    def _resolve_params(self, params: Dict[str, Any], batch_value: Any = None, batch_by: str = None) -> Dict[str, Any]:
        """
        解析参数，替换占位符
        
        支持的占位符：
            - {stock_code}: 股票代码（如果 batch_by="stock_code"）
            - {start_date}: 开始日期
            - {end_date}: 结束日期
            - {context.key}: 上下文中的其他值
        """
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # 替换占位符
                if batch_value and batch_by and f"{{{batch_by}}}" in value:
                    value = value.replace(f"{{{batch_by}}}", str(batch_value))
                
                # 替换上下文占位符
                if "{start_date}" in value:
                    value = value.replace("{start_date}", self.context.get("start_date", ""))
                if "{end_date}" in value:
                    value = value.replace("{end_date}", self.context.get("end_date", ""))
                
                # 替换通用上下文占位符 {context.key}
                if value.startswith("{context.") and value.endswith("}"):
                    context_key = value[9:-1]  # 去掉 "{context." 和 "}"
                    value = self.context.get(context_key, value)
                
                resolved[key] = value
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                resolved[key] = self._resolve_params(value, batch_value, batch_by)
            elif isinstance(value, list):
                # 处理列表
                resolved[key] = [
                    self._resolve_params(item, batch_value, batch_by) if isinstance(item, dict)
                    else item for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def _get_batch_values(self, batch_by: str) -> List[Any]:
        """
        根据 batch_by 字段获取批量值列表
        
        支持的 batch_by：
            - "stock_code": 从 context.stock_codes 获取
            - 其他：从 context 中获取对应的列表
        """
        if batch_by == "stock_code":
            return self.context.get("stock_codes", [])
        else:
            return self.context.get(batch_by, [])


class ThreadDecisionMaker:
    """线程决策器：根据 Job 数量决定是否使用多线程"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化线程决策器
        
        Args:
            config: 配置项
                - min_jobs_for_multithread: 启用多线程的最小 Job 数量（默认 10）
                - max_workers: 最大线程数（默认 None，自动计算）
                - min_workers: 最小线程数（默认 1）
                - auto_adjust: 是否自动调整（默认 True）
        """
        self.config = config or {}
        self.min_jobs = self.config.get("min_jobs_for_multithread", 10)
        self.max_workers = self.config.get("max_workers")
        self.min_workers = self.config.get("min_workers", 1)
        self.auto_adjust = self.config.get("auto_adjust", True)
    
    def decide(self, job_count: int, api_limits: Dict[str, int] = None) -> int:
        """
        决定线程数
        
        Args:
            job_count: Job 数量
            api_limits: API 限流信息 {api_name: limit_per_minute}
        
        Returns:
            int: 线程数（1 表示单线程）
        """
        # 如果 Job 数量太少，使用单线程
        if job_count < self.min_jobs:
            return 1
        
        # 如果不自动调整，返回配置的最大线程数或 1
        if not self.auto_adjust:
            return self.max_workers or 1
        
        # 根据 API 限流计算最大并发数
        if api_limits:
            # 取最严格的限流
            min_limit = min(api_limits.values())
            # 保守估计：使用限流的 80%
            max_concurrent = int(min_limit * 0.8)
        else:
            # 默认限流：60 次/分钟
            max_concurrent = 48  # 60 * 0.8
        
        # 线程数不超过 Job 数量
        workers = min(max_concurrent, job_count)
        
        # 应用最大/最小限制
        if self.max_workers:
            workers = min(workers, self.max_workers)
        workers = max(workers, self.min_workers)
        
        return workers


class APIExecutionPlanParser:
    """API 执行计划解析器"""
    
    def __init__(self, api_plan: List[Dict[str, Any]]):
        """
        初始化解析器
        
        Args:
            api_plan: API 配置列表，格式：
                [
                    {
                        "name": "daily_kline",
                        "provider": "tushare",
                        "method": "get_daily_kline",
                        "params": {...},
                        "depends_on": [],  # 依赖的 API 名称列表（空表示无依赖）
                        "batch_by": "stock_code",  # 可选：按字段批量
                        "merge_strategy": "left_join",  # 可选：合并策略
                    },
                    {
                        "name": "daily_basic",
                        "provider": "tushare",
                        "method": "get_daily_basic",
                        "params": {...},
                        "depends_on": ["daily_kline"],  # 依赖 daily_kline（会自动串行）
                    }
                ]
        """
        self.api_plan = api_plan
        self.api_jobs: List[APIJob] = []
        self.execution_plan: Optional[ExecutionPlan] = None
    
    def parse(self) -> ExecutionPlan:
        """
        解析配置，生成执行计划
        
        Returns:
            ExecutionPlan: 执行计划
        """
        # 1. 转换为 APIJob 对象
        self._parse_api_jobs()
        
        # 2. 验证依赖关系（检查循环依赖）
        self._validate_dependencies()
        
        # 3. 拓扑排序，生成执行阶段
        stages = self._topological_sort()
        
        # 4. 收集需要的 Provider
        providers = self._collect_providers()
        
        # 5. 计算总 Job 数量（暂时返回 API 数量，后续展开）
        total_jobs = len(self.api_jobs)
        
        self.execution_plan = ExecutionPlan(
            stages=stages,
            providers=providers,
            total_jobs=total_jobs
        )
        
        return self.execution_plan
    
    def _parse_api_jobs(self):
        """解析 API 配置为 APIJob 对象"""
        self.api_jobs = []
        
        for api_config in self.api_plan:
            job = APIJob(
                api_name=api_config["name"],
                provider_name=api_config["provider"],
                method=api_config["method"],
                params=api_config.get("params", {}),
                depends_on=api_config.get("depends_on", []),
                batch_by=api_config.get("batch_by"),
                merge_strategy=api_config.get("merge_strategy"),
            )
            self.api_jobs.append(job)
    
    def _validate_dependencies(self):
        """验证依赖关系，检查循环依赖"""
        # 构建依赖图
        graph = {job.api_name: set(job.depends_on) for job in self.api_jobs}
        
        # DFS 检测循环
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for dep in graph.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    # 发现循环依赖
                    cycle = list(rec_stack) + [dep]
                    raise ValueError(f"检测到循环依赖: {' -> '.join(cycle)}")
            
            rec_stack.remove(node)
            return False
        
        for api_name in graph:
            if api_name not in visited:
                if has_cycle(api_name):
                    raise ValueError(f"检测到循环依赖")
    
    def _topological_sort(self) -> List[ExecutionStage]:
        """
        拓扑排序，将 API 分组为执行阶段
        
        返回：
            List[ExecutionStage]: 执行阶段列表，每个阶段内的 API 可以并行执行
        """
        # 构建依赖图
        api_map = {job.api_name: job for job in self.api_jobs}
        in_degree = {job.api_name: len(job.depends_on) for job in self.api_jobs}
        graph = defaultdict(list)
        
        # 构建反向图（用于拓扑排序）
        for job in self.api_jobs:
            for dep in job.depends_on:
                graph[dep].append(job.api_name)
        
        # Kahn 算法进行拓扑排序
        stages = []
        stage_id = 0
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        
        while queue:
            # 当前阶段可以并行执行的 API
            current_stage_apis = []
            
            # 处理当前层级的所有节点
            level_size = len(queue)
            for _ in range(level_size):
                api_name = queue.popleft()
                job = api_map[api_name]
                current_stage_apis.append(job)
            
            # 创建执行阶段
            # 注意：同一阶段的 API 总是可以并行执行（因为它们没有依赖关系）
            stage = ExecutionStage(
                stage_id=stage_id,
                apis=current_stage_apis,
            )
            stages.append(stage)
            stage_id += 1
            
            # 更新依赖计数，将新的可执行节点加入队列
            for api in current_stage_apis:
                for dependent in graph[api.api_name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # 检查是否所有节点都被处理（防止有未解决的依赖）
        if len([job for job in self.api_jobs if job.api_name not in [api.api_name for stage in stages for api in stage.apis]]) > 0:
            raise ValueError("拓扑排序失败：存在未解决的依赖关系")
        
        return stages
    
    def _collect_providers(self) -> Set[str]:
        """收集需要的 Provider 列表"""
        return {job.provider_name for job in self.api_jobs}
    
    def get_execution_plan(self) -> Optional[ExecutionPlan]:
        """获取执行计划"""
        return self.execution_plan


# ========== 使用示例 ==========

if __name__ == "__main__":
    # 示例配置
    api_plan = [
        {
                "name": "daily_kline",
                "provider": "tushare",
                "method": "get_daily_kline",
                "params": {"ts_code": "000001.SZ", "start_date": "20240101"},
                "depends_on": [],
                "batch_by": "stock_code",
            },
            {
                "name": "daily_basic",
                "provider": "tushare",
                "method": "get_daily_basic",
                "params": {"ts_code": "000001.SZ", "start_date": "20240101"},
                "depends_on": ["daily_kline"],  # 依赖 daily_kline，会自动串行
                "merge_strategy": "left_join",
            },
    ]
    
    # 解析
    parser = APIExecutionPlanParser(api_plan)
    plan = parser.parse()
    
    # 输出结果
    print(f"需要的 Provider: {plan.providers}")
    print(f"总 API 数量: {plan.total_jobs}")
    print(f"执行阶段数: {len(plan.stages)}")
    
    for stage in plan.stages:
        # 同一阶段的 API 总是可以并行执行
        print(f"\n阶段 {stage.stage_id} (并行执行 {len(stage.apis)} 个 API):")
        for api in stage.apis:
            print(f"  - {api.api_name} (provider: {api.provider_name}, method: {api.method})")

