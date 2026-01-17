"""
DataSource Handler 基类

简化设计，职责分离：
- Handler 职责：生成 Jobs（带 Schema）→ 框架执行
- 框架职责：解析 Job Schema → 决定执行策略 → 执行 → 返回结果
"""
# 不再使用 ABC，因为基类提供默认实现
from typing import Dict, Any, List, Optional, Tuple
from datetime import timedelta
from loguru import logger
import inspect

from core.modules.data_source.api_job import ApiJob, DataSourceTask
from core.utils.date.date_utils import DateUtils


class BaseDataSourceHandler:
    """
    DataSource Handler 基类
    
    设计原则：
    1. 基类提供默认实现，只有复杂场景才需要子类覆盖
    2. Handler 不负责存储，只负责数据获取和标准化
    3. 配置自动注入，减少子类代码
    4. 简单场景：只需要定义 data_source，其他都由基类自动处理
    
    子类必须定义：
    - data_source: 数据源名称
    - description: 描述（可选）
    - dependencies: 依赖的其他数据源列表（可选）
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
        data_manager=None,
        definition=None  # DataSourceDefinition 对象（必需）
    ):
        """
        初始化 Handler
        
        Args:
            schema: 数据源的 schema 定义
            data_manager: 数据管理器（用于数据库查询，不用于保存）
            definition: DataSourceDefinition 对象（必需，包含所有配置信息）
        
        Raises:
            ValueError: 如果 definition 为 None
        """
        if definition is None:
            raise ValueError(f"{self.__class__.__name__} 必须提供 definition 参数")
        
        self.schema = schema
        self.data_manager = data_manager
        self._definition = definition  # 标准化的配置对象
        self._providers = {}
        self._generated_tasks: List[DataSourceTask] = []  # 保存生成的 Tasks（用于 normalize 中查找）
        
        self._validate_class_attributes()
        
        # ========== 加载自定义配置（extra_config）==========
        # 将所有非标准配置项提取到 extra_config 中，方便用户直接访问
        self.extra_config = self._load_extra_config()
        
        # ========== 自动初始化配置（依赖注入）==========
        # 如果配置了简单 API，自动初始化
        try:
            self.provider_name, self.method, self.field_mapping = self._setup_simple_api_config()
            self._has_simple_api_config = True
        except (ValueError, AttributeError):
            self._has_simple_api_config = False
        
        # 如果配置了滚动刷新，自动初始化
        rolling_periods = self.get_param("rolling_periods")
        rolling_months = self.get_param("rolling_months")
        if rolling_periods is not None or rolling_months is not None:
            date_format = self.get_param("date_format", "date")
            default_rolling_periods = rolling_periods or rolling_months
            default_date_range = self.get_param("default_date_range", {"years": 5})
            self.date_format, self.rolling_periods, self.default_date_range, self.table_name, self.date_field = self._setup_rolling_config(
                default_date_format=date_format,
                default_rolling_periods=default_rolling_periods,
                default_date_range=default_date_range
            )
            self._has_rolling_config = True
        else:
            self._has_rolling_config = False
    
    def _validate_class_attributes(self):
        """验证子类是否定义了必需的类属性"""
        if self.data_source is None:
            raise ValueError(f"{self.__class__.__name__} 必须定义 data_source")
    
    def _load_extra_config(self) -> Dict[str, Any]:
        """
        加载自定义配置（extra_config）
        
        从 handler_config 中提取所有非标准配置项，放入 extra_config 字典中。
        用户可以通过 self.extra_config["key"] 或 self.extra_config.get("key", default) 访问。
        
        标准配置项（不进入 extra_config）：
        - Renew Mode 相关：renew_mode, date_format, rolling_unit, rolling_length, 
                           default_date_range, table_name, date_field, 
                           rolling_periods, rolling_months
        - API 相关：provider_name, method, requires_date_range
        
        注意：
        - 对于 dataclass，所有字段（包括默认值）都会被加载
        - 对于 dict，只有实际配置的键会被加载
        - 如果用户需要区分"未配置"和"显式设置为 None"，可以使用 self.extra_config.get("key", default)
        
        Returns:
            Dict[str, Any]: 自定义配置字典
        """
        # 标准配置项列表（这些不应该进入 extra_config）
        STANDARD_CONFIG_KEYS = {
            # Renew Mode 相关
            "renew_mode", "date_format", "rolling_unit", "rolling_length",
            "default_date_range", "table_name", "date_field",
            "rolling_periods", "rolling_months",  # 旧版兼容（已废弃）
            # API 相关
            "provider_name", "method", "requires_date_range",
            # 测试相关
            "dry_run", "test_mode",
            # 自定义逻辑（可选，但属于标准配置）
            "custom_before_fetch", "custom_normalize",
        }
        
        extra_config = {}
        
        if not self._definition or not self._definition.handler_config:
            return extra_config
        
        handler_config = self._definition.handler_config
        
        # 支持两种类型：dataclass 对象或 dict
        if hasattr(handler_config, '__dataclass_fields__'):
            # dataclass 对象：遍历所有字段
            for field_name in handler_config.__dataclass_fields__.keys():
                if field_name not in STANDARD_CONFIG_KEYS:
                    value = getattr(handler_config, field_name, None)
                    # 添加所有值（包括 None），因为用户可能显式设置为 None
                    # 如果用户需要区分"未配置"和"显式设置为 None"，可以使用 get_param()
                    extra_config[field_name] = value
        elif isinstance(handler_config, dict):
            # dict：直接遍历键
            for key, value in handler_config.items():
                if key not in STANDARD_CONFIG_KEYS:
                    extra_config[key] = value
        elif hasattr(handler_config, '__dict__'):
            # 普通对象：遍历 __dict__（兜底情况）
            for key, value in handler_config.__dict__.items():
                if not key.startswith('_') and key not in STANDARD_CONFIG_KEYS:
                    extra_config[key] = value
        
        return extra_config
    
    # ========== 核心方法（提供默认实现，子类可覆盖）==========
    
    async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
        """
        生成 Tasks（默认实现）
        
        默认实现：如果配置了简单 API（provider_name, method），自动创建 Task。
        复杂场景可以覆盖此方法。
        
        Args:
            context: 执行上下文
        
        Returns:
            List[DataSourceTask]: 一组编排好的 Tasks
        """
        # 如果配置了简单 API，自动创建 Task
        if self._has_simple_api_config:
            api_params = {}
            
            # 如果需要日期范围，从 context 获取（框架已自动计算）
            if self.requires_date_range:
                start_date = context.get("start_date")
                end_date = context.get("end_date")
                
                if start_date and end_date:
                    api_params["start_date"] = start_date
                    api_params["end_date"] = end_date
            
            # 合并其他参数
            extra_params = self.get_param("extra_params", {})
            api_params.update(extra_params)
            context_params = context.get("extra_params", {})
            api_params.update(context_params)
            
            # 创建简单的单 API 调用 Task
            task = self.create_simple_task(
                provider_name=self.provider_name,
                method=self.method,
                params=api_params
            )
            return [task]
        
        # 如果没有配置简单 API，子类必须覆盖此方法
        raise NotImplementedError(
            f"{self.__class__.__name__} 必须覆盖 fetch 方法，或配置 provider_name 和 method"
        )
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict:
        """
        将原始数据标准化为框架 schema 格式（默认实现）
        
        默认实现：如果配置了字段映射，自动应用字段映射。
        复杂场景可以覆盖此方法。
        
        Args:
            task_results: 框架执行 Tasks 后返回的结果字典 {task_id: {job_id: result}}
        
        Returns:
            标准化后的数据字典，格式符合 self.schema
        """
        # 如果配置了简单 API，自动处理
        if self._has_simple_api_config:
            # 使用默认逻辑：单 API 场景
            df = self.get_simple_result(task_results)
            
            if df is None or df.empty:
                logger.warning(f"{self.data_source} 数据查询返回空数据")
                return {"data": []}
            
            # 转换为字典列表并应用字段映射（使用辅助方法）
            records = df.to_dict('records')
            formatted = self._apply_field_mapping(records, self.field_mapping)
            
            logger.info(f"✅ {self.data_source} 数据处理完成，共 {len(formatted)} 条记录")
            
            return {"data": formatted}
        
        # 如果没有配置简单 API，子类必须覆盖此方法
        raise NotImplementedError(
            f"{self.__class__.__name__} 必须覆盖 normalize 方法，或配置 provider_name 和 method"
        )
    
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
    
    async def after_normalize(self, normalized_data: Dict, context: Dict[str, Any] = None):
        """
        标准化后的钩子
        
        可以用于：
        - 数据后处理
        - 记录日志
        - 其他自定义逻辑
        
        注意：Handler 不负责数据存储，存储由框架或外部组件负责。
        如果需要保存数据，应该在 DataSourceManager 或其他外部组件中处理。
        """
        pass
    
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
        
        自动处理（如果 Handler 未覆盖钩子函数）：
        - 滚动刷新：如果配置了 rolling_periods 或 rolling_months，自动计算日期范围
        - 数据保存：如果配置了 table_name，自动保存数据到数据库
        
        Args:
            context: 执行上下文
            executor: TaskExecutor 实例（如果为 None，框架会自动创建）
        
        Returns:
            标准化后的数据字典
        """
        # 从 config 中读取测试相关参数，合并到 context（config 优先级更高）
        if self._definition and self._definition.handler_config:
            config_dry_run = self.get_param("dry_run", None)
            config_test_mode = self.get_param("test_mode", None)
            
            # 如果 config 中配置了这些参数，覆盖 context 中的值
            if config_dry_run is not None:
                context["dry_run"] = config_dry_run
            if config_test_mode is not None:
                context["test_mode"] = config_test_mode
        
        try:
            # ========== 数据准备阶段 ==========
            # 先调用 handler 的 before_fetch（如果有自定义逻辑）
            await self.before_fetch(context)
            
            # 如果配置了 renew_mode 且 context 中没有日期范围，自动处理日期范围
            renew_mode = self.get_param("renew_mode")
            if renew_mode and renew_mode in ["incremental", "rolling", "refresh"]:
                if "start_date" not in context or "end_date" not in context:
                    await self._auto_before_fetch_by_renew_mode(context)
            
            tasks = await self.fetch(context)
            self._generated_tasks = tasks  # 保存引用，供 normalize 使用
            
            await self.after_fetch(tasks, context)
            
            # ========== 执行阶段 ==========
            # 所有 tasks 执行前的钩子
            await self.before_all_tasks_execute(tasks, context)
            
            # 框架执行 Tasks
            if executor is None:
                from core.modules.data_source.task_executor import TaskExecutor
                from core.modules.data_source.provider_instance_pool import get_provider_pool
                
                # 从 ProviderInstancePool 获取所有 providers
                provider_pool = get_provider_pool()
                providers = {}
                # 收集所有需要的 provider（从 tasks 中提取）
                for task in tasks:
                    for api_job in task.api_jobs:
                        if api_job.provider_name not in providers:
                            provider = provider_pool.get_provider(api_job.provider_name)
                            if provider:
                                providers[api_job.provider_name] = provider
                
                executor = TaskExecutor(providers=providers)
                # 设置 handler 和 context（用于单个 task 执行前后的钩子）
                executor.set_handler(self, context)
            
            task_results = await executor.execute(tasks)
            
            # 所有 tasks 执行后的钩子
            await self.after_all_tasks_execute(task_results, context)
            
            # ========== 标准化阶段 ==========
            await self.before_normalize(task_results)
            
            normalized_data = await self.normalize(task_results)
            
            # 标准化后的钩子（Handler 不负责存储）
            await self.after_normalize(normalized_data, context)
            
            # 验证数据
            if not self.validate(normalized_data):
                raise ValueError(f"数据验证失败: {self.data_source}")
            
            return normalized_data
            
        except Exception as e:
            await self.on_error(e, context)
            raise
    
    # ========== 数据验证 ==========
    
    def validate(self, data: Dict) -> bool:
        """
        验证数据是否符合 schema
        
        Args:
            data: 标准化后的数据，通常是 {"data": [...]} 格式
            
        Returns:
            bool: 是否符合规范
        """
        if not self.schema:
            return True
        
        # 如果数据是 {"data": [...]} 格式，验证列表中的每个记录
        if isinstance(data, dict) and "data" in data:
            data_list = data.get("data", [])
            if not isinstance(data_list, list):
                logger.error(f"数据验证失败: data 字段不是列表类型")
                return False
            
            # 验证列表中的每个记录
            for idx, record in enumerate(data_list):
                if not isinstance(record, dict):
                    logger.error(f"数据验证失败: 记录 {idx} 不是字典类型")
                    return False
                if not self.schema.validate(record):
                    # 找出缺失或无效的字段
                    missing_fields = []
                    for field_name, field_def in self.schema.schema.items():
                        if field_def.required and field_name not in record:
                            missing_fields.append(field_name)
                        elif field_name in record and record[field_name] is not None:
                            value = record[field_name]
                            expected_type = field_def.type
                            if not isinstance(value, expected_type):
                                try:
                                    if expected_type == int and isinstance(value, (float, str)):
                                        int(value)
                                    elif expected_type == float and isinstance(value, (int, str)):
                                        float(value)
                                    elif expected_type == str:
                                        str(value)
                                    else:
                                        missing_fields.append(f"{field_name}(类型错误: {type(value).__name__} != {expected_type.__name__})")
                                except (ValueError, TypeError):
                                    missing_fields.append(f"{field_name}(类型错误: {type(value).__name__} != {expected_type.__name__})")
                    if missing_fields:
                        logger.error(f"数据验证失败: 记录 {idx} 缺少或无效的字段: {', '.join(missing_fields)}")
                    return False
            return True
        
        # 如果数据不是 {"data": [...]} 格式，直接验证整个字典
        return self.schema.validate(data)
    
    # ========== Provider 管理 ==========
    
    def register_provider(self, name: str, provider):
        """注册 provider 实例"""
        self._providers[name] = provider
    
    def get_provider(self, name: str):
        """获取 provider 实例"""
        return self._providers.get(name)
    
    # ========== 框架提供的工具方法 ==========
    
    
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
    
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """
        获取配置参数
        
        读取顺序（优先级从高到低）：
        1. 用户配置（mapping.json 中的 handler_config）
        2. config_class 中定义的默认值（如果 handler 定义了 config_class）
        3. get_param 的 default 参数
        
        Args:
            key: 参数名
            default: 最终默认值（如果用户没配置且 config_class 也没有默认值）
        
        Returns:
            参数值
        """
        if self._definition and self._definition.handler_config:
            # handler_config 是对象（Handler 定义了 config_class）
            # 检查用户是否配置了该参数（使用 hasattr 和 getattr）
            if hasattr(self._definition.handler_config, key):
                # 用户配置了该参数（即使值是 None，也使用用户配置的值）
                # 注意：dataclass 会为所有字段创建属性，所以需要检查是否在用户配置中
                # 这里我们直接获取属性值，如果用户没配置，dataclass 会使用默认值
                value = getattr(self._definition.handler_config, key)
                # 使用 sentinel 来区分"用户显式设置为 None"和"使用默认值"
                # 但由于 dataclass 的限制，我们无法区分，所以：
                # - 如果值是 None，可能是用户设置的 None，也可能是默认值 None
                # - 如果值不是 None，肯定是用户配置的或默认值
                return value
        
        # handler_config 是 None（Handler 没有定义 config_class）
        # 或者属性不存在，返回 default
        return default
    
    def get_provider_config(self):
        """
        获取 ProviderConfig（如果存在 DataSourceDefinition）
        
        Returns:
            ProviderConfig 对象，如果不存在则返回 None
        """
        if self._definition:
            return self._definition.provider_config
        return None
    
    def get_handler_config(self):
        """
        获取 HandlerConfig（如果存在 DataSourceDefinition）
        
        Returns:
            HandlerConfig 对象，如果不存在则返回 None
        """
        if self._definition:
            return self._definition.handler_config
        return None
    
    # ========== 滚动刷新辅助方法（简化业务 Handler）==========
    
    def _setup_simple_api_config(self) -> Tuple[str, str, Dict[str, Any]]:
        """
        初始化简单 API 配置（辅助方法）
        
        从 provider_config 或 handler_config 中读取 provider_name, method, field_mapping。
        
        Returns:
            Tuple[str, str, Dict]: (provider_name, method, field_mapping)
        
        Raises:
            ValueError: 如果 method 未配置
        """
        provider_config = self.get_provider_config()
        if provider_config and provider_config.apis and len(provider_config.apis) > 0:
            first_api = provider_config.apis[0]
            provider_name = self.get_param("provider_name") or first_api.provider_name
            method = self.get_param("method") or first_api.method
            field_mapping = self.get_param("field_mapping") or first_api.field_mapping or {}
        else:
            provider_name = self.get_param("provider_name", "tushare")
            method = self.get_param("method")
            field_mapping = self.get_param("field_mapping", {})
        
        if not method:
            raise ValueError(f"{self.__class__.__name__} 必须配置 method 参数（在 handler_config 或 provider_config.apis[0] 中）")
        
        return provider_name, method, field_mapping
    
    def _setup_rolling_config(
        self,
        default_date_format: str = "date",
        default_rolling_periods: Optional[int] = None,
        default_date_range: Optional[Dict[str, int]] = None
    ) -> Tuple[str, int, Dict[str, int], str, str]:
        """
        初始化滚动刷新配置（辅助方法）
        
        Args:
            default_date_format: 默认日期格式（quarter | month | date | none）
            default_rolling_periods: 默认滚动周期数（如果为 None，根据 date_format 自动设置）
            default_date_range: 默认日期范围（如果为 None，使用 {"years": 5}）
        
        Returns:
            Tuple: (date_format, rolling_periods, default_date_range, table_name, date_field)
        """
        date_format = self.get_param("date_format", default_date_format)
        default_date_range = self.get_param("default_date_range", default_date_range or {"years": 5})
        rolling_periods = self.get_param("rolling_periods", default_rolling_periods)
        table_name = self.get_param("table_name", None)
        date_field = self.get_param("date_field", None)
        
        # 如果未配置 rolling_periods，根据 date_format 设置默认值
        if rolling_periods is None:
            if date_format == "quarter":
                rolling_periods = 4
            elif date_format == "month":
                rolling_periods = 12
            elif date_format in ["day", "date"]:  # 支持 "day" 和 "date"（向后兼容）
                rolling_periods = 30
            else:
                rolling_periods = 0
        
        # 如果未配置 table_name，使用 data_source 名称
        if table_name is None:
            table_name = self.data_source
        
        return date_format, rolling_periods, default_date_range, table_name, date_field
    
    def _calculate_rolling_date_range(
        self,
        context: Dict[str, Any],
        date_format: str,
        rolling_periods: int,
        default_date_range: Dict[str, int],
        table_name: str,
        date_field: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        计算滚动刷新日期范围（辅助方法）
        
        实现滚动刷新策略：
        1. 如果数据库为空：使用默认日期范围
        2. 如果数据库不为空：
           - 计算最新日期距离当前的时间间隔
           - 如果间隔 <= rolling_periods：滚动刷新最近 rolling_periods 个时间单位
           - 如果间隔 > rolling_periods：从最新日期开始追赶（历史追赶）
        
        Args:
            context: 执行上下文
            date_format: 日期格式（quarter | month | date | none）
            rolling_periods: 滚动刷新周期数
            default_date_range: 默认日期范围
            table_name: 数据库表名
            date_field: 数据库日期字段名（如果为 None，根据 date_format 自动识别）
        
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return context["start_date"], context["end_date"]
        
        # 获取当前日期/季度/月份
        current_date = DateUtils.get_current_date_str()
        current_value = self._get_current_value_for_format(current_date, date_format)
        
        # 从 data_manager 查询数据库获取最新日期
        latest_value = None
        if self.data_manager and rolling_periods > 0:
            try:
                model = self.data_manager.get_table(table_name)
                if model:
                    latest_record = model.load_latest()
                    if latest_record:
                        if date_field is None:
                            date_field = self._get_default_date_field_for_format(date_format)
                        latest_value = latest_record.get(date_field, '')
            except Exception as e:
                logger.warning(f"查询数据库失败: {e}")
        
        # 计算需要更新的日期范围
        if not latest_value:
            # 数据库为空：使用默认日期范围
            start_date, end_date = self._calculate_default_date_range_for_format(
                current_date, date_format, default_date_range
            )
            logger.info(f"数据库为空，使用默认日期范围: {start_date} 至 {end_date}")
        else:
            # 数据库不为空：计算时间间隔
            period_diff = self._calculate_period_diff_for_format(
                latest_value, current_value, date_format
            )
            
            if period_diff <= rolling_periods:
                # 间隔 <= rolling_periods：滚动刷新最近 rolling_periods 个时间单位
                start_value = self._subtract_periods_for_format(
                    current_value, rolling_periods, date_format
                )
                start_date = self._format_value_for_format(start_value, date_format)
                end_date = self._format_value_for_format(current_value, date_format)
                period_unit = self._get_period_unit_for_format(date_format)
                logger.info(f"滚动刷新最近 {rolling_periods} 个{period_unit}: {start_date} 至 {end_date}（数据库最新: {latest_value}）")
            else:
                # 间隔 > rolling_periods：从最新日期开始追赶
                start_value = self._add_one_period_for_format(latest_value, date_format)
                start_date = self._format_value_for_format(start_value, date_format)
                end_date = self._format_value_for_format(current_value, date_format)
                period_unit = self._get_period_unit_for_format(date_format)
                logger.info(f"历史追赶: {start_date} 至 {end_date}（数据库最新: {latest_value}，落后 {period_diff} 个{period_unit}）")
        
        return start_date, end_date
    
    def _get_current_value_for_format(self, current_date: str, date_format: str):
        """根据 date_format 获取当前值"""
        if date_format == "quarter":
            current_year = int(current_date[:4])
            current_month = int(current_date[4:6])
            if current_month <= 3:
                return (current_year, 1)
            elif current_month <= 6:
                return (current_year, 2)
            elif current_month <= 9:
                return (current_year, 3)
            else:
                return (current_year, 4)
        elif date_format == "month":
            return (int(current_date[:4]), int(current_date[4:6]))
        else:  # date_format == "day" or "date" (向后兼容)
            return current_date
    
    def _get_default_date_field_for_format(self, date_format: str) -> str:
        """根据 date_format 获取默认日期字段名"""
        if date_format == "quarter":
            return "quarter"
        elif date_format == "month":
            return "date"  # price_indexes 使用 date 字段存储月份
        else:  # date_format == "day" or "date" (向后兼容)
            return "date"
    
    def _parse_value_for_format(self, value: str, date_format: str):
        """解析日期值"""
        if date_format == "quarter":
            year = int(value[:4])
            quarter = int(value[5])
            return (year, quarter)
        elif date_format == "month":
            return (int(value[:4]), int(value[4:6]))
        else:  # date_format == "day" or "date" (向后兼容)
            return value
    
    def _format_value_for_format(self, value, date_format: str) -> str:
        """格式化日期值"""
        if date_format == "quarter":
            year, quarter = value
            return f"{year}Q{quarter}"
        elif date_format == "month":
            year, month = value
            return f"{year}{month:02d}"
        else:  # date_format == "day" or "date" (向后兼容)
            return value
    
    def _calculate_period_diff_for_format(self, latest_value: str, current_value, date_format: str) -> int:
        """计算两个日期之间的周期差"""
        latest = self._parse_value_for_format(latest_value, date_format)
        current = current_value
        
        if date_format == "quarter":
            latest_year, latest_quarter = latest
            current_year, current_quarter = current
            return (current_year - latest_year) * 4 + (current_quarter - latest_quarter)
        elif date_format == "month":
            latest_year, latest_month = latest
            current_year, current_month = current
            return (current_year - latest_year) * 12 + (current_month - latest_month)
        else:  # date_format == "day" or "date" (向后兼容)
            latest_date = DateUtils.parse_yyyymmdd(latest)
            current_date = DateUtils.parse_yyyymmdd(current)
            return (current_date - latest_date).days
    
    def _subtract_periods_for_format(self, value, periods: int, date_format: str):
        """减去 N 个周期"""
        if date_format == "quarter":
            year, quarter = value
            quarter -= periods - 1
            while quarter < 1:
                quarter += 4
                year -= 1
            return (year, quarter)
        elif date_format == "month":
            year, month = value
            month -= periods - 1
            while month < 1:
                month += 12
                year -= 1
            return (year, month)
        else:  # date_format == "day" or "date" (向后兼容)
            date = DateUtils.parse_yyyymmdd(value)
            new_date = date - timedelta(days=periods - 1)
            return DateUtils.format_to_yyyymmdd(new_date)
    
    def _add_one_period_for_format(self, latest_value: str, date_format: str):
        """添加一个周期（用于历史追赶）"""
        latest = self._parse_value_for_format(latest_value, date_format)
        
        if date_format == "quarter":
            year, quarter = latest
            quarter += 1
            if quarter > 4:
                quarter = 1
                year += 1
            return (year, quarter)
        elif date_format == "month":
            year, month = latest
            month += 1
            if month > 12:
                month = 1
                year += 1
            return (year, month)
        else:  # date_format == "day" or "date" (向后兼容)
            date = DateUtils.parse_yyyymmdd(latest)
            new_date = date + timedelta(days=1)
            return DateUtils.format_to_yyyymmdd(new_date)
    
    def _get_period_unit_for_format(self, date_format: str) -> str:
        """获取周期单位名称"""
        if date_format == "quarter":
            return "季度"
        elif date_format == "month":
            return "个月"
        else:  # date_format == "day" or "date" (向后兼容)
            return "天"
    
    def _calculate_default_date_range_for_format(
        self,
        current_date: str,
        date_format: str,
        default_date_range: Dict[str, int]
    ) -> Tuple[str, str]:
        """根据配置计算默认日期范围"""
        current_year = int(current_date[:4])
        current_month = int(current_date[4:6])
        
        if date_format == "quarter":
            if current_month <= 3:
                current_quarter = 1
            elif current_month <= 6:
                current_quarter = 2
            elif current_month <= 9:
                current_quarter = 3
            else:
                current_quarter = 4
            
            if "years" in default_date_range:
                years = default_date_range["years"]
                start_year = current_year - years
                start_quarter = 1
            elif "quarters" in default_date_range:
                quarters = default_date_range["quarters"]
                start_year = current_year
                start_quarter = current_quarter - quarters + 1
                while start_quarter < 1:
                    start_quarter += 4
                    start_year -= 1
            else:
                start_year = current_year - 5
                start_quarter = 1
            
            end_date = f"{current_year}Q{current_quarter}"
            start_date = f"{start_year}Q{start_quarter}"
            
        elif date_format == "month":
            if "years" in default_date_range:
                years = default_date_range["years"]
                start_year = current_year - years
                start_month = 1
            elif "months" in default_date_range:
                months = default_date_range["months"]
                start_year = current_year
                start_month = current_month - months + 1
                while start_month < 1:
                    start_month += 12
                    start_year -= 1
            else:
                start_year = current_year - 3
                start_month = 1
            
            end_date = f"{current_year}{current_month:02d}"
            start_date = f"{start_year}{start_month:02d}"
            
        else:  # date_format == "day" or "date" (向后兼容) or "none"
            if "years" in default_date_range:
                years = default_date_range["years"]
                start_date = DateUtils.get_date_before_days(current_date, years * 365)
            elif "days" in default_date_range:
                days = default_date_range["days"]
                start_date = DateUtils.get_date_before_days(current_date, days)
            else:
                start_date = DateUtils.get_date_before_days(current_date, 5 * 365)
            
            end_date = current_date
        
        return start_date, end_date
    
    def _apply_field_mapping(
        self,
        records: List[Dict[str, Any]],
        field_mapping: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        应用字段映射（辅助方法）
        
        Args:
            records: 原始记录列表
            field_mapping: 字段映射规则（Dict[str, str] 或 Dict[str, Callable]）
        
        Returns:
            映射后的记录列表
        """
        formatted = []
        
        for item in records:
            mapped = {}
            
            # 应用字段映射
            if field_mapping:
                for target_field, source_field in field_mapping.items():
                    if callable(source_field):
                        mapped[target_field] = source_field(item)
                    elif isinstance(source_field, str):
                        value = item.get(source_field)
                        if value is not None:
                            if isinstance(value, (int, float)):
                                mapped[target_field] = float(value)
                            else:
                                mapped[target_field] = value
                        else:
                            mapped[target_field] = 0.0 if target_field not in ['date', 'quarter', 'month'] else ''
                    else:
                        mapped[target_field] = item.get(source_field) if source_field in item else None
            else:
                mapped = item.copy()
            
            if mapped:
                formatted.append(mapped)
        
        return formatted
    
    # ========== 自动处理辅助方法（简化 Handler 实现）==========
    
    def _should_auto_handle_renew_mode(self) -> bool:
        """
        判断是否应该自动处理 renew_mode
        
        条件：
        1. 配置了 renew_mode（incremental | rolling | refresh）
        2. Handler 没有覆盖 before_fetch 方法（使用基类的默认实现）
        """
        # 检查是否配置了 renew_mode
        renew_mode = self.get_param("renew_mode")
        if not renew_mode or renew_mode not in ["incremental", "rolling", "refresh"]:
            return False
        
        # 检查 Handler 是否覆盖了 before_fetch
        # 通过检查方法定义的位置来判断是否被覆盖
        handler_before_fetch = getattr(self.__class__, 'before_fetch', None)
        if handler_before_fetch:
            # 获取方法定义的文件路径
            try:
                method_file = inspect.getfile(handler_before_fetch)
                base_file = inspect.getfile(BaseDataSourceHandler.before_fetch)
                # 如果方法定义在不同的文件中，说明被覆盖了
                if method_file != base_file:
                    return False
            except (OSError, TypeError):
                # 如果无法获取文件信息，使用更保守的策略
                # 检查方法是否在基类中定义
                if handler_before_fetch.__qualname__ != 'BaseDataSourceHandler.before_fetch':
                    return False
        
        return True
    
    async def _auto_before_fetch_by_renew_mode(self, context: Dict[str, Any]):
        """
        根据 renew_mode 自动处理日期范围（before_fetch）
        
        使用独立的 service 类处理不同 mode 的逻辑，核心代码分离，便于 debug。
        """
        if context is None:
            context = {}
        
        renew_mode = self.get_param("renew_mode")
        
        if renew_mode == "incremental":
            await self._auto_before_fetch_incremental(context)
        elif renew_mode == "rolling":
            await self._auto_before_fetch_rolling(context)
        elif renew_mode == "refresh":
            await self._auto_before_fetch_refresh(context)
        else:
            # 未知的 renew_mode，不自动处理
            logger.warning(f"未知的 renew_mode: {renew_mode}，跳过自动处理")
    
    async def _auto_before_fetch_incremental(self, context: Dict[str, Any]):
        """
        自动处理增量更新（incremental mode）
        
        使用 IncrementalRenewService 处理逻辑。
        """
        from core.modules.data_source.services import IncrementalRenewService
        
        # 获取配置
        date_format = self.get_param("date_format", "day")
        table_name = self.get_param("table_name")
        date_field = self.get_param("date_field")
        
        if not table_name or not date_field:
            logger.warning("Incremental mode 需要 table_name 和 date_field，跳过自动处理")
            return
        
        # 使用 service 计算日期范围
        service = IncrementalRenewService(data_manager=self.data_manager)
        start_date, end_date = service.calculate_date_range(
            date_format=date_format,
            table_name=table_name,
            date_field=date_field,
            context=context
        )
        
        context["start_date"] = start_date
        context["end_date"] = end_date
    
    async def _auto_before_fetch_refresh(self, context: Dict[str, Any]):
        """
        自动处理全量刷新（refresh mode）
        
        使用 RefreshRenewService 处理逻辑。
        """
        from core.modules.data_source.services import RefreshRenewService
        
        # 获取配置
        date_format = self.get_param("date_format", "day")
        default_date_range = self.get_param("default_date_range", {})
        
        # 使用 service 计算日期范围
        service = RefreshRenewService(data_manager=self.data_manager)
        start_date, end_date = service.calculate_date_range(
            date_format=date_format,
            default_date_range=default_date_range,
            context=context
        )
        
        context["start_date"] = start_date
        context["end_date"] = end_date
    
    async def _auto_before_fetch_rolling(self, context: Dict[str, Any]):
        """
        自动处理滚动刷新（rolling mode）
        
        使用 RollingRenewService 处理逻辑。
        """
        from core.modules.data_source.services import RollingRenewService
        
        # 获取滚动刷新配置（优先使用新的 rolling_unit/rolling_length）
        rolling_unit = self.get_param("rolling_unit")
        rolling_length = self.get_param("rolling_length")
        
        # 向后兼容：如果没有配置新的参数，使用旧的 rolling_periods/rolling_months
        if rolling_unit is None or rolling_length is None:
            rolling_periods = self.get_param("rolling_periods")
            rolling_months = self.get_param("rolling_months")
            
            if rolling_months is not None:
                rolling_unit = "month"
                rolling_length = rolling_months
            elif rolling_periods is not None:
                # 根据 date_format 推断 rolling_unit
                date_format = self.get_param("date_format", "day")
                if date_format == "quarter":
                    rolling_unit = "quarter"
                elif date_format == "month":
                    rolling_unit = "month"
                else:
                    rolling_unit = "day"
                rolling_length = rolling_periods
            else:
                logger.warning("Rolling mode 需要 rolling_unit/rolling_length 或 rolling_periods/rolling_months，跳过自动处理")
                return
        
        # 获取其他配置
        date_format = self.get_param("date_format", "day")
        table_name = self.get_param("table_name")
        date_field = self.get_param("date_field")
        
        if not table_name or not date_field:
            logger.warning("Rolling mode 需要 table_name 和 date_field，跳过自动处理")
            return
        
        # 如果未配置 date_field，根据 date_format 自动识别
        if date_field is None:
            date_field = self._get_default_date_field_for_format(date_format)
        
        # 使用 service 计算日期范围
        service = RollingRenewService(data_manager=self.data_manager)
        start_date, end_date = service.calculate_date_range(
            date_format=date_format,
            rolling_unit=rolling_unit,
            rolling_length=rolling_length,
            table_name=table_name,
            date_field=date_field,
            context=context
        )
        
        context["start_date"] = start_date
        context["end_date"] = end_date
    
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

