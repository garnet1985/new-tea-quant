"""
LEGACY MODULE - v1 DataSource handler pipeline.

This file defines the original `BaseDataSourceHandler` used by early data_source
handlers together with `DataSourceTask`, `TaskExecutor` and the `services/*`
renew-mode pipeline.

It is retained for backward compatibility with existing handlers under
`userspace/data_source/handlers/*`. New data-source handlers should extend
`core.modules.data_source.base_class.base_handler.BaseHandler` and use the
new data_class/* and service/* helpers instead of this legacy stack.

See `core/modules/data_source/ARCHIVE.md` or architecture docs for details.
"""
# 不再使用 ABC，因为基类提供默认实现
from typing import Dict, Any, List, Optional
from loguru import logger

from core.modules.data_source.data_classes import ApiJob, DataSourceTask
from core.utils.date.date_utils import DateUtils
from core.global_enums.enums import UpdateMode, TimeUnit


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
        
        # ========== 初始化 Services ==========
        from core.modules.data_source.services import APIJobManager, DataValidator, RenewModeService
        
        # 初始化 API Job Manager
        self._api_job_manager = APIJobManager()
        handler_config = self.get_handler_config()
        if handler_config:
            self._api_job_manager.init_api_jobs(handler_config)
        
        # 初始化 Data Validator
        self._data_validator = DataValidator()
        
        # 初始化 Renew Mode Service
        self._renew_mode_service = RenewModeService(data_manager=data_manager)
    
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
            # API 相关（现在在 apis 字典中）
            "apis", "requires_date_range",
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
        生成 Tasks（默认实现，适用于简单数据源）
        
        默认行为：
        - 如果 handler_config.apis 中只配置了一个 API：
          - 使用配置的 provider_name / method / params
          - 结合 context 中的 start_date / end_date（由 renew_mode 自动计算）
          - 生成一个包含单个 ApiJob 的 DataSourceTask
        
        更复杂的场景（如多 API、按股票拆分等）应在子类中覆盖此方法。
        """
        handler_config = self.get_handler_config()
        apis = getattr(handler_config, "apis", None) if handler_config else None
        
        if not apis:
            raise NotImplementedError(
                f"{self.__class__.__name__} 必须覆盖 fetch 方法或在 handler_config.apis 中配置至少一个 API"
            )
        
        if not isinstance(apis, dict) or len(apis) != 1:
            # 默认实现只支持单 API 场景，多 API 由子类自行编排
            raise NotImplementedError(
                f"{self.__class__.__name__} 默认 fetch 仅支持单 API 场景，请在子类中自定义 fetch"
            )
        
        api_name = list(apis.keys())[0]
        context = context or {}
        
        # 构建 API 参数
        api_params: Dict[str, Any] = {}
        
        # 是否需要日期范围：优先使用 handler_config.requires_date_range，其次使用类属性
        requires_date_range = getattr(handler_config, "requires_date_range", getattr(self, "requires_date_range", False))
        if requires_date_range:
            start_date = context.get("start_date")
            end_date = context.get("end_date")
            if start_date is not None:
                api_params["start_date"] = start_date
            if end_date is not None:
                api_params["end_date"] = end_date
        
        # 允许通过配置和 context 注入额外参数
        extra_params = self.get_param("extra_params", {}) or {}
        api_params.update(extra_params)
        context_params = context.get("extra_params") or {}
        api_params.update(context_params)
        
        # 从缓存的 ApiJob 创建实例，只修改 params
        api_job = self.get_api_job_with_params(
            name=api_name,
            params=api_params,
        )
        
        task = DataSourceTask(
            task_id=f"{self.data_source}_task",
            api_jobs=[api_job],
            description=f"获取 {self.data_source} 数据",
        )
        
        return [task]
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict:
        """
        将原始数据标准化为框架 schema 格式（默认实现，适用于简单数据源）
        
        默认行为：
        - 假定只有一个 Task + 一个 ApiJob（由默认 fetch 创建）
        - 使用字段映射（handler_config.apis[*].field_mapping）将 DataFrame 转为记录列表
        
        更复杂的场景（多 API 合并等）应在子类中覆盖此方法。
        """
        handler_config = self.get_handler_config()
        apis = getattr(handler_config, "apis", None) if handler_config else None
        
        if not apis:
            raise NotImplementedError(
                f"{self.__class__.__name__} 必须覆盖 normalize 方法或在 handler_config.apis 中配置至少一个 API"
            )
        
        if not isinstance(apis, dict) or len(apis) != 1:
            raise NotImplementedError(
                f"{self.__class__.__name__} 默认 normalize 仅支持单 API 场景，请在子类中自定义 normalize"
            )
        
        api_name = list(apis.keys())[0]
        api_cfg = apis.get(api_name) or {}
        field_mapping = api_cfg.get("field_mapping", {}) or {}
        
        # 获取简单 Task 结果（默认使用 {data_source}_task / 第一个 job）
        df = self.get_simple_result(task_results)
        
        if df is None or getattr(df, "empty", False):
            logger.info(f"{self.data_source} 数据查询返回空数据")
            return {"data": []}
        
        records = df.to_dict("records")
        formatted = self._apply_field_mapping(records, field_mapping)
        
        logger.info(f"✅ {self.data_source} 数据处理完成，共 {len(formatted)} 条记录")
        return {"data": formatted}
    
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

    def _validate_data_for_save(self, normalized_data: Dict[str, Any]):
        """
        通用的数据验证辅助方法：
        - 确保 normalized_data 是字典
        - 提取并验证其中的 'data' 字段为 list
        - 空数据时返回空列表，调用方据此判断是否需要落库

        目前被部分 Handler（如宏观指标、企业财务等）复用。
        """
        if not isinstance(normalized_data, dict):
            logger.warning(f"{self.data_source} normalized_data 不是字典，无法保存")
            return []

        data_list = normalized_data.get("data")
        if not data_list:
            # 空数据属于正常情况，不算错误
            return []

        if not isinstance(data_list, list):
            logger.warning(f"{self.data_source} normalized_data['data'] 不是 list，实际类型: {type(data_list)}")
            return []

        return data_list

    def _save_data_with_clean_nan(
        self,
        normalized_data: Dict[str, Any],
        context: Dict[str, Any],
        save_method: callable,
        data_source_name: str = None
    ) -> None:
        """
        保存数据到数据库的辅助方法（带 NaN 清理）
        
        这是一个通用的保存方法，适用于需要清理 NaN 值的数据源。
        使用场景：lpr, shibor, gdp 等宏观经济数据。
        
        Args:
            normalized_data: 标准化后的数据（包含 'data' 键）
            context: 执行上下文
            save_method: 保存方法（如 self.data_manager.macro.save_lpr_data）
            data_source_name: 数据源名称（用于日志，如果为 None 使用 self.data_source）
        """
        context = context or {}
        data_source_name = data_source_name or self.data_source
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.info(f"🧪 干运行模式：跳过 {data_source_name} 数据保存")
            return
        
        if not self.data_manager:
            logger.warning(f"DataManager 未初始化，无法保存 {data_source_name} 数据")
            return
        
        # 验证数据格式
        data_list = normalized_data.get("data") if isinstance(normalized_data, dict) else None
        if not data_list:
            logger.debug(f"{data_source_name} 数据为空，无需保存")
            return
        
        try:
            # 清理 NaN 值
            from core.infra.db.helpers.db_helpers import DBHelper
            data_list = DBHelper.clean_nan_in_list(data_list, default=0.0)
            
            # 使用传入的保存方法保存数据
            count = save_method(data_list)
            logger.info(f"✅ {data_source_name} 数据保存完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存 {data_source_name} 数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
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
            valid_modes = [UpdateMode.INCREMENTAL.value, UpdateMode.ROLLING.value, UpdateMode.REFRESH.value]
            if renew_mode and renew_mode in valid_modes:
                if "start_date" not in context or "end_date" not in context:
                    await self._auto_before_fetch_by_renew_mode(context)
                    # 检查日期范围是否成功设置
                    if "start_date" in context and "end_date" in context:
                        logger.debug(f"  ✅ 日期范围已设置: {context['start_date']} 至 {context['end_date']}")
                    else:
                        logger.warning(f"  ⚠️ 日期范围未设置，可能导致 fetch 失败")
            
            tasks = await self.fetch(context)
            self._generated_tasks = tasks  # 保存引用，供 normalize 使用
            
            # 检查 tasks 是否为空
            if not tasks:
                logger.warning(f"⚠️ {self.data_source} Handler 的 fetch 方法返回了空的 tasks 列表，跳过执行")
                return {"data": []}
            
            # 记录生成的 tasks 信息
            total_jobs = sum(len(task.api_jobs) for task in tasks)
            logger.info(f"📋 {self.data_source} Handler 生成了 {len(tasks)} 个 Tasks，共 {total_jobs} 个 API Jobs")
            
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
                    if not task.api_jobs:
                        logger.warning(f"⚠️ Task {task.task_id} 没有 api_jobs，跳过")
                        continue
                    for api_job in task.api_jobs:
                        if api_job.provider_name not in providers:
                            provider = provider_pool.get_provider(api_job.provider_name)
                            if provider:
                                providers[api_job.provider_name] = provider
                            else:
                                logger.warning(f"⚠️ Provider {api_job.provider_name} 未找到，可能无法执行 API 请求")
                
                if not providers:
                    logger.error(f"❌ {self.data_source} Handler 没有可用的 providers，无法执行 API 请求")
                    return {"data": []}
                
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
        return self._data_validator.validate(data, self.schema)
    
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
    
    def get_handler_config(self):
        """
        获取 HandlerConfig（如果存在 DataSourceDefinition）
        
        Returns:
            HandlerConfig 对象，如果不存在则返回 None
        """
        if self._definition:
            return self._definition.handler_config
        return None
    
    def get_api_job(self, name: str) -> Optional[ApiJob]:
        """
        根据 name 获取缓存的 ApiJob 实例
        
        Args:
            name: API 名称（配置中的 key）
        
        Returns:
            ApiJob 实例，如果不存在则返回 None
        """
        return self._api_job_manager.get_api_job(name)
    
    def get_api_job_with_params(
        self,
        name: str,
        params: Dict[str, Any],
        job_id: Optional[str] = None,
        **kwargs
    ) -> ApiJob:
        """
        获取 ApiJob 实例并设置新的 params（便捷方法）
        
        从缓存的 ApiJob 实例创建新实例，只修改 params 和其他指定字段。
        这是推荐的用法，避免在 fetch 中直接创建 ApiJob。
        
        Args:
            name: API 名称（配置中的 key）
            params: API 调用参数（动态生成，会与配置中的默认 params 合并）
            job_id: Job ID（可选）
            **kwargs: 其他要修改的字段（depends_on, priority, timeout 等）
        
        Returns:
            ApiJob 对象（新实例）
        
        Raises:
            ValueError: 如果 API 不存在
        
        Example:
            # 在 fetch 方法中使用
            api_job = self.get_api_job_with_params(
                name="finance_data",
                params={
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                job_id=f"{stock_id}_finance"
            )
        """
        return self._api_job_manager.get_api_job_with_params(
            name=name,
            params=params,
            job_id=job_id,
            **kwargs
        )
    
    
    
    # ========== 滚动刷新辅助方法（简化业务 Handler）==========
    
    
    
    def _get_default_date_field_for_format(self, date_format: str) -> str:
        """根据 date_format 获取默认日期字段名（业务逻辑）"""
        if date_format == TimeUnit.QUARTER.value:
            return "quarter"
        elif date_format == TimeUnit.MONTH.value:
            return "date"  # price_indexes 使用 date 字段存储月份
        else:  # date_format == TimeUnit.DAY.value or "date" (兼容旧格式)
            return "date"
    
    
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
    
    async def _auto_before_fetch_by_renew_mode(self, context: Dict[str, Any]):
        """
        根据 renew_mode 自动处理日期范围（before_fetch）
        
        使用 RenewModeService 统一处理所有 renew_mode 的逻辑。
        """
        if context is None:
            context = {}
        
        renew_mode = self.get_param("renew_mode")
        valid_modes = [UpdateMode.INCREMENTAL.value, UpdateMode.ROLLING.value, UpdateMode.REFRESH.value]
        
        if not renew_mode or renew_mode not in valid_modes:
            logger.warning(f"未知的 renew_mode: {renew_mode}，跳过自动处理")
            return
        
        # 获取配置
        date_format = self.get_param("date_format", TimeUnit.DAY.value)
        table_name = self.get_param("table_name")
        date_field = self.get_param("date_field")
        rolling_unit = self.get_param("rolling_unit")
        rolling_length = self.get_param("rolling_length")
        default_date_range = self.get_param("default_date_range", {})
        
        # 如果未配置 date_field，根据 date_format 自动识别
        if date_field is None and date_format != TimeUnit.NONE.value:
            date_field = self._get_default_date_field_for_format(date_format)
        
        # 使用 RenewModeService 统一处理
        try:
            start_date, end_date = self._renew_mode_service.calculate_date_range(
                renew_mode=renew_mode,
                date_format=date_format,
                context=context,
                table_name=table_name,
                date_field=date_field,
                rolling_unit=rolling_unit,
                rolling_length=rolling_length,
                default_date_range=default_date_range
            )
            
            context["start_date"] = start_date
            context["end_date"] = end_date
        except ValueError as e:
            logger.warning(f"自动处理 renew_mode 失败: {e}")
            return
    
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

