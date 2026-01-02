"""
DataSource Handler 基类

简化设计，职责分离：
- Handler 职责：生成 Jobs（带 Schema）→ 框架执行
- 框架职责：解析 Job Schema → 决定执行策略 → 执行 → 返回结果
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from loguru import logger

from app.data_source.api_job import ApiJob, DataSourceTask


class BaseDataSourceHandler(ABC):
    """
    DataSource Handler 基类
    
    设计原则：
    1. Handler 简单化：只需要生成 Jobs，不需要理解复杂的配置格式
    2. 框架智能化：框架根据 Job Schema 自动决定执行策略
    3. 灵活性优先：Handler 完全控制 Job 生成逻辑
    4. 代码可读性：直接看代码就知道在做什么
    
    子类必须定义：
    - data_source: 数据源名称
    - description: 描述
    - dependencies: 依赖的其他数据源列表
    """
    
    # ========== 类属性（子类必须定义）==========
    data_source: str = None          # 数据源名称，如 "stock_list"
    description: str = ""            # Handler 描述
    dependencies: List[str] = []      # 依赖的其他数据源
    
    # ========== 可选的类属性 ==========
    rate_limit: Optional[int] = None          # Handler 级别的限流
    batch_size: Optional[int] = None          # 批量处理大小
    requires_date_range: bool = False         # 是否需要日期范围
    
    def __init__(
        self, 
        schema, 
        params: Dict[str, Any] = None, 
        data_manager=None
    ):
        """
        初始化 Handler
        
        Args:
            schema: 数据源的 schema 定义
            params: 从 mapping.json 传入的自定义参数
            data_manager: 数据管理器（用于数据库查询）
        """
        self.schema = schema
        self.params = params or {}
        self.data_manager = data_manager
        self._providers = {}
        self._generated_tasks: List[DataSourceTask] = []  # 保存生成的 Tasks（用于 normalize 中查找）
        
        self._validate_class_attributes()
    
    def _validate_class_attributes(self):
        """验证子类是否定义了必需的类属性"""
        if self.data_source is None:
            raise ValueError(f"{self.__class__.__name__} 必须定义 data_source")
    
    # ========== 核心抽象方法（子类必须实现）==========
    
    @abstractmethod
    async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
        """
        生成 Tasks
        
        Args:
            context: 执行上下文，包含：
                - start_date: 开始日期（incremental 需要）
                - end_date: 结束日期（incremental 需要）
                - stock_codes: 股票代码列表（如果需要）
                - force_refresh: 是否强制刷新
                - ... 其他依赖数据源的数据
        
        Returns:
            List[DataSourceTask]: 一组编排好的 Tasks（每个 Task 包含多个 ApiJobs）
        
        注意：
        - Handler 完全控制 Task 和 ApiJob 生成逻辑
        - 可以查询数据库、计算参数、处理复杂逻辑
        - 参数必须已计算好（不需要占位符替换）
        - 一个 Task 代表一个业务任务（如：获取复权因子、获取股票 K 线）
        - 一个 Task 可以包含多个 ApiJobs（如：Tushare API + AKShare API）
        """
        pass
    
    @abstractmethod
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict:
        """
        将原始数据标准化为框架 schema 格式
        
        Args:
            task_results: 框架执行 Tasks 后返回的结果字典 {task_id: {job_id: result}}
        
        Returns:
            标准化后的数据字典，格式符合 self.schema
        """
        pass
    
    # ========== 可选的钩子方法 ==========
    
    # ========== 数据准备阶段 ==========
    async def before_fetch(self, context: Dict[str, Any]):
        """
        获取数据前的钩子（可用于数据准备）
        
        可以用于：
        - 查询数据库获取上次更新时间
        - 计算参数
        - 准备执行上下文
        """
        pass
    
    async def after_fetch(self, tasks: List[DataSourceTask], context: Dict[str, Any]):
        """
        生成 Tasks 后的钩子（Tasks 还未执行）
        
        可以用于：
        - 验证 Tasks
        - 记录日志
        - 统计 Tasks 和 ApiJobs 数量
        """
        pass
    
    # ========== 执行阶段 ==========
    
    async def before_all_tasks_execute(self, tasks: List[DataSourceTask], context: Dict[str, Any]):
        """
        所有 tasks 执行前的钩子（在所有 tasks 开始执行前统一调用）
        
        可以用于：
        - 最后调整 Tasks 或 ApiJobs
        - 记录执行前的状态
        - 验证 Tasks 配置
        - 设置执行参数
        - 初始化统计计数器
        
        Args:
            tasks: 即将执行的所有 Tasks 列表
            context: 执行上下文
        """
        pass
    
    async def before_single_task_execute(self, task: DataSourceTask, context: Dict[str, Any]):
        """
        单个 task 执行前的钩子（每个 task 开始执行前调用）
        
        可以用于：
        - 针对单个 task 的预处理
        - 记录单个 task 的执行开始时间
        - 验证单个 task 的配置
        - 设置 task 级别的执行参数
        
        Args:
            task: 即将执行的单个 Task
            context: 执行上下文
        """
        pass
    
    async def after_single_task_execute(
        self,
        task_id: str,
        task_result: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """
        单个 task 执行后的钩子（每个 task 执行完成后立即调用）
        
        可以用于：
        - 单个 task 的结果预处理
        - 单个 task 的数据保存（增量保存，实现断点续传）
        - 单个 task 的日志记录
        - 单个 task 的错误处理
        
        Args:
            task_id: 已完成的 Task ID
            task_result: 该 Task 的执行结果 {job_id: result}
            context: 执行上下文
        
        注意：
        - 此方法在每个 task 完成后立即调用，适合增量保存场景
        - 如果在这里保存数据，可以实现断点续传（即使后续 tasks 失败，已完成的也能保存）
        - task_result 的结构：{job_id: result}
        """
        pass
    
    async def after_all_tasks_execute(
        self, 
        task_results: Dict[str, Dict[str, Any]], 
        context: Dict[str, Any]
    ):
        """
        所有 tasks 执行完成后的钩子（在所有 tasks 执行完成后统一调用）
        
        可以用于：
        - 合并所有 tasks 的结果
        - 计算全局业务逻辑
        - 统计和日志记录
        - 最终的数据清理和后处理
        
        Args:
            task_results: 所有 Tasks 的执行结果字典 {task_id: {job_id: result}}
            context: 执行上下文
        
        注意：
        - 此时可以访问所有 Tasks 的执行结果
        - task_results 的结构：{task_id: {job_id: result}}
        - 可以修改 task_results，传递给后续的 normalize
        - 如果实现了 after_single_task_execute 进行增量保存，这里主要用于统计和最终处理
        """
        pass
    
    
    # ========== 标准化阶段 ==========
    async def before_normalize(self, raw_data: Any):
        """
        标准化前的钩子
        
        可以用于：
        - 数据预处理
        - 数据验证
        """
        pass
    
    async def after_normalize(self, normalized_data: Dict):
        """
        标准化后的钩子
        
        可以用于：
        - 数据后处理
        - 记录日志
        - 保存数据到数据库（通过 _save_to_data_manager）
        """
        pass
    
    # ========== 数据保存辅助方法 ==========
    
    def _validate_data_for_save(self, normalized_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        验证数据格式，返回数据列表
        
        这是一个辅助方法，用于验证标准化后的数据格式。
        具体的保存逻辑应该在 Handler 的钩子函数中实现。
        
        Args:
            normalized_data: 标准化后的数据（包含 'data' 键）
        
        Returns:
            数据列表，如果验证失败返回空列表
        
        注意：
        - 此方法只做数据验证，不执行保存操作
        - 具体的保存逻辑应该在 Handler 的钩子函数中实现
        """
        if not self.data_manager:
            logger.warning(f"{self.data_source} Handler 未设置 data_manager，无法保存数据")
            return []
        
        if 'data' not in normalized_data:
            logger.warning(f"{self.data_source} 数据格式不正确，缺少 'data' 键")
            return []
        
        data_list = normalized_data['data']
        if not data_list:
            logger.debug(f"{self.data_source} 没有数据需要保存")
            return []
        
        return data_list
    
    # ========== 错误处理 ==========
    async def on_error(self, error: Exception, context: Dict[str, Any]):
        """错误处理钩子"""
        logger.error(f"{self.data_source} 处理出错: {error}")
        raise
    
    # ========== 完整的执行流程（模板方法）==========
    
    async def execute(
        self, 
        context: Dict[str, Any],
        executor=None
    ) -> Dict:
        """
        执行 Handler 的完整生命周期流程
        
        这是 Handler 的主要执行入口，包含完整的生命周期：
        1. 数据准备阶段：before_fetch → fetch → after_fetch
        2. 执行阶段：
           - before_all_tasks_execute（所有 tasks 执行前）
           - 对每个 task：
             - before_single_task_execute（单个 task 执行前）
             - 执行 task
             - after_single_task_execute（单个 task 执行后）
           - after_all_tasks_execute（所有 tasks 执行后）
        3. 标准化阶段：before_normalize → normalize → after_normalize
        
        Args:
            context: 执行上下文
            executor: TaskExecutor 实例（如果为 None，框架会自动创建）
        
        Returns:
            标准化后的数据字典
        """
        try:
            # ========== 数据准备阶段 ==========
            await self.before_fetch(context)
            
            tasks = await self.fetch(context)
            self._generated_tasks = tasks  # 保存引用，供 normalize 使用
            
            await self.after_fetch(tasks, context)
            
            # ========== 执行阶段 ==========
            # 所有 tasks 执行前的钩子
            await self.before_all_tasks_execute(tasks, context)
            
            # 框架执行 Tasks
            if executor is None:
                from app.data_source.task_executor import TaskExecutor
                executor = TaskExecutor()  # TODO: 需要传入 providers 和 rate_limiter
                # 设置 handler 和 context（用于单个 task 执行前后的钩子）
                executor.set_handler(self, context)
            
            task_results = await executor.execute(tasks)
            
            # 所有 tasks 执行后的钩子
            await self.after_all_tasks_execute(task_results, context)
            
            # ========== 标准化阶段 ==========
            await self.before_normalize(task_results)
            
            normalized_data = await self.normalize(task_results)
            
            await self.after_normalize(normalized_data)
            
            # 验证数据
            if not self.validate(normalized_data):
                raise ValueError(f"数据验证失败: {self.data_source}")
            
            return normalized_data
            
        except Exception as e:
            await self.on_error(e, context)
            raise
    
    # ========== 数据验证 ==========
    
    def validate(self, data: Dict) -> bool:
        """验证数据是否符合 schema"""
        if self.schema:
            return self.schema.validate(data)
        return True
    
    # ========== Provider 管理 ==========
    
    def register_provider(self, name: str, provider):
        """注册 provider 实例"""
        self._providers[name] = provider
    
    def get_provider(self, name: str):
        """获取 provider 实例"""
        return self._providers.get(name)
    
    # ========== 框架提供的工具方法 ==========
    
    async def execute_tasks(
        self, 
        tasks: List[DataSourceTask],
        max_workers: Optional[int] = None,
        use_rate_limit: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        执行一组 Tasks（框架提供）
        
        - 自动处理依赖关系（拓扑排序）
        - 自动应用限流
        - 自动决定线程数
        - 返回 {task_id: {job_id: result}} 字典
        
        注意：Handler 可以直接调用，也可以让框架自动调用
        """
        from app.data_source.task_executor import TaskExecutor
        executor = TaskExecutor()  # TODO: 需要传入 providers 和 rate_limiter
        return await executor.execute(tasks)
    
    # ========== 辅助方法 ==========
    
    def create_simple_task(
        self,
        provider_name: str,
        method: str,
        params: Dict[str, Any] = None,
        task_id: str = None
    ) -> DataSourceTask:
        """
        创建简单的单 API 调用 Task（辅助方法）
        
        适用于简单的数据源，只需要一次 API 调用，不需要复杂的依赖和限流处理。
        
        Args:
            provider_name: Provider 名称（如 "tushare"）
            method: Provider 方法名（如 "get_stock_list"）
            params: API 调用参数
            task_id: Task ID（可选，默认使用 data_source 名称）
        
        Returns:
            DataSourceTask: 包含单个 ApiJob 的 Task
        
        Example:
            # 简单场景：只需要一次 API 调用
            task = self.create_simple_task(
                provider_name="tushare",
                method="get_stock_list",
                params={"fields": "ts_code,name"}
            )
            return [task]
        """
        if task_id is None:
            task_id = f"{self.data_source}_task"
        
        api_job = ApiJob(
            provider_name=provider_name,
            method=method,
            params=params or {}
        )
        
        return DataSourceTask(
            task_id=task_id,
            api_jobs=[api_job]
        )
    
    def get_simple_result(
        self,
        raw_data: Dict[str, Any],
        task_id: str = None,
        job_index: int = 0
    ) -> Any:
        """
        获取简单 Task 的执行结果（辅助方法）
        
        适用于只有一个 Task 和一个 ApiJob 的简单场景。
        
        Args:
            raw_data: 框架返回的原始数据 {task_id: {job_id: result}}
            task_id: Task ID（可选，默认使用 data_source 名称）
            job_index: Job 索引（默认 0，即第一个 job）
        
        Returns:
            API 调用的原始结果（通常是 DataFrame 或其他类型）
        
        Example:
            # 在 normalize 中使用
            df = self.get_simple_result(raw_data)
            # 处理 df...
        """
        if task_id is None:
            task_id = f"{self.data_source}_task"
        
        job_id = f"{task_id}_job_{job_index}"
        
        if task_id not in raw_data:
            raise ValueError(f"无法找到 Task 结果: {task_id}")
        
        if job_id not in raw_data[task_id]:
            raise ValueError(f"无法找到 Job 结果: {task_id}/{job_id}")
        
        return raw_data[task_id][job_id]
    
    def get_task_by_id(self, task_id: str) -> Optional[DataSourceTask]:
        """根据 task_id 查找 Task（用于 normalize 中查找 Task 信息）"""
        for task in self._generated_tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def get_api_job_by_id(self, job_id: str) -> Optional[ApiJob]:
        """根据 job_id 查找 ApiJob（用于 normalize 中查找 ApiJob 信息）"""
        for task in self._generated_tasks:
            for api_job in task.api_jobs:
                if api_job.job_id == job_id:
                    return api_job
        return None
    
    def group_results_by_task(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        按 Task 分组结果（辅助方法）
        
        Args:
            task_results: {task_id: {job_id: result}}
        
        Returns:
            {task_id: {job_id: result}}（已经是按 Task 分组的，这里主要是为了保持接口一致性）
        """
        return task_results
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """获取配置参数"""
        return self.params.get(key, default)
    
    # ========== 元信息 ==========
    
    def get_metadata(self) -> Dict:
        """获取 Handler 元信息"""
        return {
            "data_source": self.data_source,
            "description": self.description,
            "dependencies": self.dependencies,
            "rate_limit": self.rate_limit,
            "batch_size": self.batch_size,
            "requires_date_range": self.requires_date_range,
        }
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(data_source={self.data_source})>"

