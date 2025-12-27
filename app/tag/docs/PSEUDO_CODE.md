# Tag 系统伪代码设计

本文档包含 TagManager、BaseTagCalculator 和 DataManager Tag API 的伪代码设计。

---

## 0. 配置常量

```python
# app/tag/config.py 或 app/tag/__init__.py

# Scenarios 根目录配置
DEFAULT_SCENARIOS_ROOT = "app/tag/scenarios"  # 相对于项目根目录

# 版本回退配置
ALLOW_VERSION_ROLLBACK = False  # 是否允许版本回退后继续执行（默认 False，需要用户明确配置为 True）
```

---

## 1. TagManager 伪代码

```python
class TagManager:
    """
    Tag Manager - 统一管理所有业务场景（Scenario）
    
    职责：
    1. 发现和加载所有 scenario calculators
    2. 检查 settings 文件存在性
    3. 统一验证所有 settings（schema 校验）
    4. 提供统一的接口访问 calculators
    5. 支持手动注册 scenario（未来实现）
    
    注意：
    - 元信息的创建在 Calculator 中处理（支持手动注册）
    - Settings 验证在 TagManager 层统一处理
    """
    
    def __init__(self, data_mgr=None):
        """
        初始化 TagManager
        
        Args:
            data_mgr: DataManager 实例（用于访问数据库）
        """
        # 从配置读取 scenarios 根目录（DEFAULT_SCENARIOS_ROOT）
        # 初始化字典：
        #   - self.scenarios: Dict[str, Type[BaseTagCalculator]]  # scenario 名称 -> calculator 类
        #   - self.scenarios_settings: Dict[str, Dict]  # scenario 名称 -> settings 字典
        #   - self.scenarios_instances: Dict[str, BaseTagCalculator]  # scenario 名称 -> calculator 实例（缓存）
        # 初始化 data_mgr
        # 初始化 DataManager 的 tag 服务：
        #   - self.tag_service = data_mgr.get_tag_service()  # TagService（DataManager 提供）
        # 注意：不在这里发现 scenarios，延迟到 run() 时
        pass
    
    def run(self, data_source_mgr=None):
        """
        执行所有 scenarios 的计算（入口函数）
        
        Args:
            data_source_mgr: DataSourceManager 实例（可选）
        """
        # 1. 发现所有 scenarios（调用 _discover_and_register_calculators）
        #    - 遍历 scenarios 目录
        #    - 加载 settings 和 calculator 类
        #    - 存储到缓存
        # 
        # 2. 统一验证所有 settings（调用 _validate_all_settings）
        #    - 统一做 schema 校验
        #    - 抛出早期错误
        # 
        # 3. 对每个 enable 的 scenario（同步执行）：
        #    a. 获取 calculator 实例（自动创建并缓存）
        #    b. 调用 calculator.run(data_source_mgr)
        #    c. 等待完成（同步）
        #    d. 如果出错，记录日志但继续执行其他 scenarios
        pass
    
    def _discover_and_register_calculators(self):
        """
        发现所有 scenario calculators（扫描静态 settings / modules）
        
        只做发现和加载，不注册到数据库
        """
        # 如果 scenarios 目录不存在，直接返回
        # 遍历 scenarios 目录下的所有子目录
        # 对每个子目录（scenario_name）：
        #   1. 检查 calculator.py 是否存在（递归查找）
        #   2. 检查 settings.py 是否存在（递归查找）
        #   3. 如果缺少文件，记录警告并跳过
        #   4. 加载 settings（调用 _load_settings）
        #   5. 加载 calculator 类（调用 _load_calculator）
        #   6. 存储到 self.scenarios 字典：scenario_name -> calculator_class
        #   7. 存储到 self.scenarios_settings 字典：scenario_name -> settings
        #   注意：不在这里注册到数据库，延迟到 calculator.run() 时
        pass
    
    def _validate_all_settings(self):
        """
        统一验证所有 settings（schema 校验，抛出早期错误）
        """
        # 对每个 scenario 的 settings：
        #   1. 验证基本结构（scenario.name, scenario.version, calculator.base_term）
        #   2. 验证必需字段
        #   3. 验证枚举值（KlineTerm, UpdateMode, VersionChangeAction）
        #   4. 如果验证失败，抛出 ValueError 并记录详细的错误信息
        pass
    
    def register_scenario(self, settings_dict: Dict[str, Any], data_source_mgr=None):
        """
        手动注册 scenario（支持"无 settings 文件"的入口）
        
        未来实现：允许用户传入 settings 字典，创建"隐形"的 tag 计算器
        
        Args:
            settings_dict: Settings 字典（格式同 settings.py 中的 Settings）
            data_source_mgr: DataSourceManager 实例（可选）
        """
        # 1. 验证 settings_dict（调用 _validate_settings）
        # 2. 创建 calculator 实例（从 settings_dict 创建，没有 settings 文件）
        # 3. 调用 calculator.run(data_source_mgr)
        # 注意：这是未来功能，当前可以先不实现
        pass
    
    def _load_settings(self, settings_file: Path) -> Dict[str, Any]:
        """
        加载 settings 文件
        
        Args:
            settings_file: settings.py 文件路径
            
        Returns:
            Dict[str, Any]: Settings 字典
            
        Raises:
            ValueError: settings 文件格式错误
        """
        # 动态导入模块
        # 提取 Settings 变量
        # 验证 Settings 是字典类型
        # 验证必需字段：scenario.name, scenario.version, calculator.base_term
        # 返回 Settings 字典
        pass
    
    def _load_calculator(self, calculator_file: Path) -> Type[BaseTagCalculator]:
        """
        加载 calculator 类
        
        Args:
            calculator_file: calculator.py 文件路径
            
        Returns:
            Type[BaseTagCalculator]: Calculator 类
        """
        # 动态导入模块
        # 查找继承自 BaseTagCalculator 的类
        # 返回 Calculator 类
        pass
    
    # ========================================================================
    # Calculator 管理（自动创建实例）
    # ========================================================================
    
    def get_calculator(self, scenario_name: str) -> Optional[Type[BaseTagCalculator]]:
        """
        获取指定 scenario 的 calculator 类
        
        Args:
            scenario_name: scenario 名称（目录名）
            
        Returns:
            Type[BaseTagCalculator] 或 None
        """
        # 从 self.scenarios 字典中获取
        pass
    
    def get_calculator_instance(
        self,
        scenario_name: str,
        data_source_mgr=None
    ) -> Optional[BaseTagCalculator]:
        """
        获取指定 scenario 的 calculator 实例（自动创建并缓存）
        
        TagManager 自动管理 calculator 实例的创建和缓存
        
        Args:
            scenario_name: scenario 名称（目录名）
            data_source_mgr: DataSourceManager 实例（可选，用于数据加载）
            
        Returns:
            BaseTagCalculator 实例或 None
        """
        # 1. 检查缓存（self.scenarios_instances）
        # 2. 如果已缓存，直接返回
        # 3. 如果未缓存：
        #    - 获取 calculator 类
        #    - 获取 settings
        #    - 确定 settings 文件路径
        #    - 创建 calculator 实例：
        #        * settings_path
        #        * data_mgr=self.data_mgr
        #        * data_source_mgr=data_source_mgr
        #        * tag_value_model=self.tag_service.get_tag_value_model()
        #    - 缓存到 self.scenarios_instances
        #    - 返回实例
        pass
    
    def list_scenarios(self) -> List[str]:
        """
        列出所有可用的 scenario 名称
        
        Returns:
            List[str]: scenario 名称列表
        """
        # 返回 self.scenarios 字典的 keys
        pass
    
    def reload(self):
        """
        重新发现所有 scenarios
        
        用于动态加载新添加的 scenario
        """
        # 清空字典
        # 调用 _load_scenarios()
        pass
```

---

## 2. BaseTagCalculator 伪代码

```python
class BaseTagCalculator(ABC):
    """
    Tag Calculator 基类
    
    职责：
    1. 配置管理（读取、验证、处理）
    2. 数据加载（钩子函数，默认实现支持股票）
    3. 计算执行（调用用户实现的 calculate_tag）
    4. Tag 值保存（通过 TagService）
    5. 其他钩子（初始化、清理、错误处理）
    """
    
    def __init__(
        self,
        settings_path: str,
        data_mgr=None,
        data_source_mgr=None,
        tag_service=None
    ):
        """
        初始化 Calculator
        
        Args:
            settings_path: settings 文件路径（相对于 calculator 同级目录）
            data_mgr: DataManager 实例
            data_source_mgr: DataSourceManager 实例（可选，用于数据加载）
            tag_service: TagService 实例（DataManager 提供，用于数据库操作）
        """
        # 保存参数
        # 获取 calculator 文件路径
        # 读取、验证和处理配置
        # 提取 calculator 配置到实例变量
        # 处理 tags 配置
        # 初始化 tag_service（如果为 None，从 data_mgr 获取）
        # 调用 on_init() 钩子
        pass
    
    # ========================================================================
    # 1. 配置管理
    # ========================================================================
    
    def _load_and_process_settings(
        self,
        settings_path: str,
        calculator_path: str
    ) -> Dict[str, Any]:
        """
        加载并处理 settings 文件
        
        Args:
            settings_path: settings 文件路径（相对路径）
            calculator_path: calculator 文件路径
            
        Returns:
            Dict[str, Any]: 处理后的 settings 字典
        """
        # 1. 读取 settings 文件
        # 2. 验证 scenario 必需字段（name, version）
        # 3. 验证 calculator 必需字段（base_term）
        # 4. 验证 tags 必需字段（至少一个 tag，每个 tag 有 name, display_name）
        # 5. 应用默认值（display_name, description, required_terms, required_data, core, performance）
        # 6. 验证枚举值（base_term, update_mode, on_version_change）
        # 7. 返回处理后的 settings
        pass
    
    def _validate_scenario_fields(self, settings: Dict[str, Any]):
        """
        验证 scenario 配置字段
        """
        # 检查 scenario 存在
        # 检查 scenario.name（必需）
        # 检查 scenario.version（必需）
        # 检查 scenario.on_version_change（可选，默认 REFRESH_SCENARIO）
        pass
    
    def _validate_calculator_fields(self, settings: Dict[str, Any]):
        """
        验证 calculator 配置字段
        """
        # 检查 calculator 存在
        # 检查 calculator.base_term（必需，必须在枚举中）
        # 检查 calculator.performance.update_mode（可选，默认 INCREMENTAL）
        pass
    
    def _validate_tags_fields(self, settings: Dict[str, Any]):
        """
        验证 tags 配置字段
        """
        # 检查 tags 存在且是列表
        # 检查至少有一个 tag
        # 对每个 tag：
        #   - 检查 name（必需）
        #   - 检查 display_name（必需）
        #   - 检查 tag name 唯一性
        pass
    
    def _apply_defaults(self, settings: Dict[str, Any]):
        """
        应用默认值
        """
        # scenario.display_name: 默认同 scenario.name
        # scenario.description: 默认 ""
        # scenario.on_version_change: 默认 REFRESH_SCENARIO
        # calculator.required_terms: 默认 []
        # calculator.required_data: 默认 []
        # calculator.core: 默认 {}
        # calculator.performance: 默认 {}
        # calculator.performance.update_mode: 默认 INCREMENTAL
        # calculator.performance.max_workers: 默认自动分配
        # tag.display_name: 默认同 tag.name（代码层面处理）
        # tag.description: 默认 ""
        pass
    
    def _extract_calculator_config(self):
        """
        提取 calculator 配置到实例变量（方便访问）
        """
        # self.scenario_name = settings["scenario"]["name"]
        # self.scenario_version = settings["scenario"]["version"]
        # self.base_term = settings["calculator"]["base_term"]
        # self.required_terms = settings["calculator"]["required_terms"]
        # self.required_data = settings["calculator"]["required_data"]
        # self.core = settings["calculator"]["core"]
        # self.performance = settings["calculator"]["performance"]
        pass
    
    def _process_tags_config(self) -> List[Dict[str, Any]]:
        """
        处理 tags 配置（合并 calculator 和 tag 配置）
        
        Returns:
            List[Dict[str, Any]]: 处理后的 tags 配置列表
        """
        # 对每个 tag：
        #   1. 合并配置（调用 _merge_tag_config）
        #   2. 添加到列表
        # 返回列表
        pass
    
    def _merge_tag_config(self, tag_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并 calculator 和 tag 配置
        
        注意：tag 级别不支持 core 和 performance，只在 calculator 级别配置
        
        Args:
            tag_config: tag 配置字典
            
        Returns:
            Dict[str, Any]: 合并后的配置
        """
        # 复制 calculator 配置
        # 添加 tag 元信息（name, display_name, description）
        # 返回合并后的配置
        pass
    
    # ========================================================================
    # 2. 数据加载（钩子函数，默认实现支持股票）
    # ========================================================================
    
    def load_entity_data(
        self,
        entity_id: str,
        entity_type: str = "stock",
        as_of_date: str = None
    ) -> Dict[str, Any]:
        """
        加载实体历史数据（默认实现支持股票）
        
        用户可以重写此方法以支持自定义数据源
        
        Args:
            entity_id: 实体ID（如股票代码 "000001.SZ"）
            entity_type: 实体类型（默认 "stock"）
            as_of_date: 截止日期（格式：YYYYMMDD，如果为 None，使用最新日期）
            
        Returns:
            Dict[str, Any]: 历史数据字典
                {
                    "klines": {
                        "daily": [...],
                        "weekly": [...],
                        ...
                    },
                    "finance": {...},
                    ...
                }
        """
        # 初始化 historical_data = {}
        # 
        # 1. 加载 K 线数据
        #    - 获取所有需要的周期（base_term + required_terms）
        #    - 对每个周期：
        #        * 如果 data_source_mgr 存在，调用 data_source_mgr.load_kline()
        #        * 否则，从 DataManager 加载（通过 tag_service 或 data_mgr）
        #    - 存储到 historical_data["klines"]
        # 
        # 2. 加载其他数据源
        #    - 遍历 required_data
        #    - 对每个数据源：
        #        * 如果 data_source_mgr 存在，调用对应的 load 方法
        #        * 否则，从 DataManager 加载（通过 tag_service 或 data_mgr）
        #    - 存储到 historical_data
        # 
        # 返回 historical_data
        pass
    
    # ========================================================================
    # 3. 计算执行（用户实现）
    # ========================================================================
    
    @abstractmethod
    def calculate_tag(
        self,
        entity_id: str,
        entity_type: str,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_config: Dict[str, Any]
    ) -> Optional[Any]:
        """
        计算 tag（用户实现）
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            as_of_date: 业务日期（格式：YYYYMMDD）
            historical_data: 历史数据字典
            tag_config: 当前 tag 的配置（已合并 calculator 和 tag 配置）
                - base_term: 基础周期
                - required_terms: 需要的周期列表
                - required_data: 需要的数据源列表
                - core: calculator 的 core 参数（所有 tags 共享）
                - performance: calculator 的 performance 配置（所有 tags 共享）
                - tag_meta: tag 元信息（name, display_name, description）
        
        Returns:
            Dict[str, Any] 或 None:
                - 如果返回 None，不创建 tag
                - 如果返回字典，格式：
                    {
                        "value": str,  # 标签值（字符串）
                        "start_date": str,  # 可选，起始日期（YYYYMMDD）
                        "end_date": str,  # 可选，结束日期（YYYYMMDD）
                    }
        """
        pass
    
    # ========================================================================
    # 4. Tag 值保存（通过 TagService）
    # ========================================================================
    
    def save_tag_value(
        self,
        tag_definition_id: int,
        entity_id: str,
        entity_type: str,
        as_of_date: str,
        value: str,
        start_date: str = None,
        end_date: str = None
    ):
        """
        保存 tag 值到数据库（通过 TagService）
        
        Args:
            tag_definition_id: Tag Definition ID
            entity_id: 实体ID
            entity_type: 实体类型
            as_of_date: 业务日期
            value: 标签值（字符串）
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）
        """
        # 通过 tag_service.save_tag_value() 保存
        # 主键：(entity_id, tag_definition_id, as_of_date)
        # 如果已存在，更新；否则插入
        pass
    
    # ========================================================================
    # 4. 执行入口（Calculator 入口函数）
    # ========================================================================
    
    def run(self, data_source_mgr=None):
        """
        Calculator 入口函数（由 TagManager.run() 调用）
        
        流程：
        1. 确保元信息存在（ensure_metadata）
        2. 处理版本变更和更新模式（renew_or_create_values）
        
        Args:
            data_source_mgr: DataSourceManager 实例（可选）
        """
        # 1. 确保元信息存在
        #    scenario, tag_defs = self.ensure_metadata()
        # 
        # 2. 处理版本变更和更新模式
        #    self.renew_or_create_values()
        pass
    
    def ensure_metadata(self):
        """
        确保元信息存在（scenario 和 tag definitions）
        
        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]]]: (scenario, tag_definitions)
        """
        # 1. 确保 scenario 存在
        #    scenario = self.ensure_scenario()
        # 
        # 2. 确保 tag definitions 存在
        #    tag_defs = self.ensure_tags(scenario)
        # 
        # 返回 scenario, tag_defs
        pass
    
    def ensure_scenario(self) -> Dict[str, Any]:
        """
        确保 scenario 存在（如果不存在则创建）
        
        Returns:
            Dict[str, Any]: Scenario 记录
        """
        # 1. 查询数据库中该 scenario name 的所有版本
        #    existing_scenarios = self.tag_service.list_scenarios(
        #        scenario_name=self.scenario_name
        #    )
        # 
        # 2. 查找 settings.version 是否已存在
        #    target_scenario = None
        #    for s in existing_scenarios:
        #        if s["version"] == self.scenario_version:
        #            target_scenario = s
        #            break
        # 
        # 3. 如果已存在，返回该 scenario
        #    if target_scenario:
        #        return target_scenario
        # 
        # 4. 如果不存在，创建新的 scenario（通过 TagService）
        #    scenario_id = self.tag_service.create_scenario(
        #        name=self.scenario_name,
        #        version=self.scenario_version,
        #        display_name=self.settings["scenario"].get("display_name", self.scenario_name),
        #        description=self.settings["scenario"].get("description", "")
        #    )
        #    target_scenario = self.tag_service.get_scenario(self.scenario_name, self.scenario_version)
        # 
        # 5. 返回 scenario
        pass
    
    def ensure_tags(self, scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        确保 tag definitions 存在（如果不存在则创建）
        
        Args:
            scenario: Scenario 记录
            
        Returns:
            List[Dict[str, Any]]: Tag Definition 列表
        """
        # 1. 查询该 scenario 下的所有 tag definitions
        #    existing_tags = self.tag_service.get_tag_definitions(scenario_id=scenario["id"])
        # 
        # 2. 对每个 settings.tags 中的 tag：
        #    a. 检查是否已存在（通过 name）
        #    b. 如果不存在，创建新的 tag definition
        #    c. 添加到列表
        # 
        # 3. 返回 tag definitions 列表
        pass
    
    def renew_or_create_values(self):
        """
        处理版本变更和更新模式
        
        流程：
        1. 处理版本变更（handle_version_change）
        2. 根据版本变更结果和 update_mode 计算（handle_update_mode）
        """
        # 1. 处理版本变更
        #    version_action = self.handle_version_change()
        # 
        # 2. 根据版本变更结果和 update_mode 计算
        #    self.handle_update_mode(version_action)
        pass
    
    def handle_version_change(self) -> str:
        """
        处理版本变更
        
        逻辑：
        1. 如果 settings.version 在数据库中已存在且 is_legacy=0（active）：
           - version_action = "NO_CHANGE"（版本未变，继续使用）
        2. 如果 settings.version 在数据库中已存在但 is_legacy=1（legacy）：
           - 这是用户把 version 改回到以前存在过的版本（版本回退）
           - 查找当前的 active 版本（is_legacy=0）
           - 如果存在 active 版本：
               * 标记之前的 active 版本为 legacy（调用 mark_scenario_as_legacy）
           - 把当前版本（settings.version）设置为 legacy=0（active）
               * 调用 update_scenario，设置 is_legacy=0
           - 注意：不删除旧的 tag definitions 和 tag values
           - 确保 tag definitions 存在（调用 ensure_tags，如果不存在则创建）
           - 按照该版本的 update_mode 继续（incremental 或 refresh）
           - version_action = "ROLLBACK"（版本回退，按照 update_mode 继续）
        3. 如果 settings.version 在数据库中不存在：
           - 读取 on_version_change 配置
           - version_action = on_version_change（REFRESH_SCENARIO 或 NEW_SCENARIO）
           - 如果是 NEW_SCENARIO：
               * 创建新 scenario（调用 create_new_scenario）
               * 查找当前的 active 版本（is_legacy=0）
               * 如果存在 active 版本：
                   - 标记之前的 active 版本为 legacy（调用 mark_scenario_as_legacy）
               * 清理旧版本（调用 cleanup_legacy_versions）
           - 如果是 REFRESH_SCENARIO：
               * 查找当前的 active 版本（is_legacy=0）
               * 如果存在 active 版本：
                   - 更新 scenario（调用 update_scenario，更新 version 等字段）
                   - 删除旧的 tag definitions 和 tag values（调用 delete_tag_definitions_by_scenario 和 delete_tag_values_by_scenario）
               * 如果不存在 active 版本：
                   - 创建新 scenario（调用 create_scenario）
               * 创建新的 tag definitions（调用 ensure_tags）
        
        Returns:
            str: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
        """
        # 1. 查询数据库中该 scenario name 的所有版本
        #    db_scenarios = self.tag_service.list_scenarios(
        #        scenario_name=self.scenario_name
        #    )
        # 
        # 2. 查找 settings.version 是否在数据库中已存在
        #    existing_scenario = None
        #    for s in db_scenarios:
        #        if s["version"] == self.scenario_version:
        #            existing_scenario = s
        #            break
        # 
        # 3. 如果已存在且 is_legacy=0（active）：
        #    - version_action = "NO_CHANGE"
        #    - 返回 version_action
        # 
        # 4. 如果已存在但 is_legacy=1（legacy）：
        #    - 这是用户把 version 改回到以前存在过的版本（版本回退）
        #    - 检查全局配置 ALLOW_VERSION_ROLLBACK
        #    - 如果 ALLOW_VERSION_ROLLBACK = False：
        #        * 记录严重警告日志：
        #          logger.error(
        #              "Version rollback detected but not allowed: "
        #              f"scenario={self.scenario_name}, version={self.scenario_version}. "
        #              "Version rollback may cause data inconsistency. "
        #              "Only rollback version if calculator logic is also rolled back. "
        #              "To allow version rollback, set ALLOW_VERSION_ROLLBACK=True in config."
        #          )
        #        * 抛出 ValueError，阻止继续执行
        #    - 如果 ALLOW_VERSION_ROLLBACK = True：
        #        * 记录警告日志：
        #          logger.warning(
        #              "Version rollback detected: "
        #              f"scenario={self.scenario_name}, version={self.scenario_version}. "
        #              "WARNING: Version rollback may cause data inconsistency. "
        #              "Only rollback version if calculator logic is also rolled back. "
        #              "User is responsible for ensuring algorithm consistency."
        #          )
        #        * 查找当前的 active 版本（is_legacy=0）
        #        * 如果存在 active 版本：
        #            - 标记之前的 active 版本为 legacy（调用 mark_scenario_as_legacy）
        #        * 把当前版本（existing_scenario）设置为 legacy=0（active）
        #            - 调用 update_scenario(existing_scenario["id"], is_legacy=0)
        #        * 注意：不删除旧的 tag definitions 和 tag values
        #            - 保留历史数据，让用户可以查看
        #        * 确保 tag definitions 存在（调用 ensure_tags，如果不存在则创建）
        #            - self.ensure_tags(existing_scenario)
        #        * version_action = "ROLLBACK"（版本回退，按照 update_mode 继续）
        #    - 返回 version_action
        # 
        # 5. 如果不存在：
        #    - 读取 on_version_change 配置
        #    - version_action = on_version_change（REFRESH_SCENARIO 或 NEW_SCENARIO）
        #    - 如果是 NEW_SCENARIO：
        #        * 创建新 scenario（调用 create_new_scenario）
        #        * 查找当前的 active 版本（is_legacy=0）
        #        * 如果存在 active 版本：
        #            - 标记之前的 active 版本为 legacy（调用 mark_scenario_as_legacy）
        #        * 清理旧版本（调用 cleanup_legacy_versions）
        #    - 如果是 REFRESH_SCENARIO：
        #        * 查找当前的 active 版本（is_legacy=0）
        #        * 如果存在 active 版本：
        #            - 更新 scenario（调用 update_scenario，更新 version 等字段）
        #            - 删除旧的 tag definitions 和 tag values（调用 delete_tag_definitions_by_scenario 和 delete_tag_values_by_scenario）
        #                * self.tag_service.delete_tag_definitions_by_scenario(active_scenario["id"])
        #                * self.tag_service.delete_tag_values_by_scenario(active_scenario["id"])
        #        * 如果不存在 active 版本：
        #            - 创建新 scenario（调用 create_scenario）
        #        * 创建新的 tag definitions（调用 ensure_tags）
        #    - 返回 version_action
        pass
    
    def handle_update_mode(self, version_action: str):
        """
        根据版本变更结果和 update_mode 计算
        
        Args:
            version_action: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")
        """
        # 1. 获取 scenario 和 tag definitions
        #    scenario = self.ensure_scenario()
        #    tag_defs = self.ensure_tags(scenario)
        # 
        # 2. 确定计算日期范围
        #    if version_action == "NO_CHANGE":
        #        # 按 update_mode 计算
        #        update_mode = self.performance.get("update_mode", "INCREMENTAL")
        #        if update_mode == "INCREMENTAL":
        #            # 从上次计算的最大 as_of_date 继续
        #            start_date = self._get_max_as_of_date(tag_defs) + 1
        #            end_date = self._get_latest_trading_date()
        #        elif update_mode == "REFRESH":
        #            # 从 start_date 到 end_date
        #            start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
        #            end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
        #    elif version_action == "ROLLBACK":
        #        # 版本回退：按照该版本的 update_mode 继续
        #        update_mode = self.performance.get("update_mode", "INCREMENTAL")
        #        # 记录警告日志
        #        logger.warning(
        #            f"Version rollback detected: scenario={self.scenario_name}, "
        #            f"version={self.scenario_version}. "
        #            f"Continuing with update_mode={update_mode}. "
        #            f"User is responsible for ensuring algorithm consistency."
        #        )
        #        if update_mode == "INCREMENTAL":
        #            # 从上次计算的最大 as_of_date 继续
        #            start_date = self._get_max_as_of_date(tag_defs) + 1
        #            end_date = self._get_latest_trading_date()
        #        elif update_mode == "REFRESH":
        #            # 重新计算所有数据
        #            start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
        #            end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
        #    else:
        #        # version_action == "NEW_SCENARIO" 或 "REFRESH_SCENARIO"
        #        # 重新计算所有 tags
        #        start_date = self.settings["calculator"].get("start_date") or self._get_default_start_date()
        #        end_date = self.settings["calculator"].get("end_date") or self._get_latest_trading_date()
        # 
        # 3. 获取实体列表
        #    entities = self._get_entity_list()
        # 
        # 4. 对每个实体：
        #    a. 加载历史数据（调用 self.load_entity_data）
        #    b. 对每个 tag：
        #        * 调用 self.calculate_tag()
        #        * 如果返回结果，保存 tag 值（调用 self.save_tag_value）
        #    c. 如果出错，调用 self.on_calculate_error()
        # 
        # 5. 调用 self.on_finish()
        pass
    
    def create_new_scenario(self) -> Dict[str, Any]:
        """
        创建新 scenario（NEW_SCENARIO 场景）
        
        Returns:
            Dict[str, Any]: 新创建的 Scenario 记录
        """
        # 1. 创建新的 scenario（通过 TagService）
        #    new_scenario_id = self.tag_service.create_scenario(
        #        name=self.scenario_name,
        #        version=self.scenario_version,
        #        display_name=self.settings["scenario"].get("display_name", self.scenario_name),
        #        description=self.settings["scenario"].get("description", "")
        #    )
        # 
        # 2. 创建新的 tag definitions
        #    tag_defs = self.ensure_tags(new_scenario)
        # 
        # 3. 返回新 scenario
        pass
    
    def cleanup_legacy_versions(self, scenario_name: str, keep_n: int = 3):
        """
        清理旧的 legacy versions
        
        如果 legacy version 数量 >= keep_n，删除最老的
        
        Args:
            scenario_name: Scenario 名称
            keep_n: 最大保留的 legacy version 数量（默认 3，可配置）
        """
        # 1. 查询所有 legacy scenarios（按 created_at 排序，最老的在前）
        #    legacy_scenarios = self.tag_service.list_scenarios(
        #        scenario_name=scenario_name,
        #        include_legacy=True
        #    )
        #    legacy_scenarios = [s for s in legacy_scenarios if s["is_legacy"] == 1]
        #    legacy_scenarios.sort(key=lambda x: x["created_at"])
        # 
        # 2. 如果数量 >= keep_n：
        #    - 计算需要删除的数量：len(legacy_scenarios) - keep_n + 1
        #    - 删除最老的 scenarios（调用 tag_service.delete_scenario）
        # 
        # 3. 返回清理结果（删除了多少个）
        pass
    
    
    # ========================================================================
    # 5. 其他钩子函数（可选实现）
    # ========================================================================
    
    def on_init(self):
        """
        初始化钩子（可选实现）
        """
        pass
    
    def on_tag_created(
        self,
        tag_definition_id: int,
        entity_id: str,
        as_of_date: str,
        value: str
    ):
        """
        Tag 创建后钩子（可选实现）
        """
        pass
    
    def on_calculate_error(
        self,
        entity_id: str,
        as_of_date: str,
        tag_name: str,
        error: Exception
    ):
        """
        计算错误钩子（可选实现）
        """
        pass
    
    def should_continue_on_error(self) -> bool:
        """
        错误时是否继续（可选实现）
        
        Returns:
            bool: True 继续，False 停止
        """
        return True
    
    def on_finish(self):
        """
        完成钩子（可选实现）
        """
        pass
```

---

## 3. DataManager Tag Service 伪代码

```python
# app/data_manager/data_services/tag/tag_service.py

class TagService:
    """
    Tag Service - DataManager 提供的 Tag 数据库操作服务
    
    职责：
    1. Scenario 和 Tag Definition 的 CRUD 操作
    2. Tag Value 的 CRUD 操作
    3. 数据查询和过滤
    """
    
    def __init__(self, data_mgr):
        """
        初始化 TagService
        
        Args:
            data_mgr: DataManager 实例
        """
        # 初始化数据库模型：
        #   - self.tag_scenario_model = data_mgr.get_model("tag_scenario")
        #   - self.tag_definition_model = data_mgr.get_model("tag_definition")
        #   - self.tag_value_model = data_mgr.get_model("tag_value")
        pass
    
    # ========================================================================
    # Scenario 操作
    # ========================================================================
    
    def create_scenario(
        self,
        name: str,
        version: str,
        display_name: str = None,
        description: str = ""
    ) -> int:
        """
        创建 Scenario
        
        Args:
            name: 业务场景名称
            version: 版本号
            display_name: 显示名称（如果为 None，默认同 name）
            description: 描述
            
        Returns:
            int: Scenario ID
            
        Raises:
            ValueError: 如果 scenario 已存在（name + version）
        """
        # 检查 scenario 是否已存在（name + version）
        # 如果已存在，抛出 ValueError
        # 如果 display_name 为 None，使用 name
        # 插入 tag_scenario 表
        # 返回 scenario_id
        pass
    
    def update_scenario(
        self,
        scenario_id: int,
        display_name: str = None,
        description: str = None,
        is_legacy: int = None
    ):
        """
        更新 Scenario
        
        Args:
            scenario_id: Scenario ID
            display_name: 显示名称（可选）
            description: 描述（可选）
            is_legacy: 是否遗留（可选，0 或 1）
        """
        # 更新 tag_scenario 表
        # 只更新提供的字段
        # 如果 is_legacy 被更新，同时更新该 scenario 下的所有 tag definitions 的 is_legacy
        pass
    
    def get_scenario(
        self,
        scenario_name: str,
        version: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取 Scenario 信息
        
        Args:
            scenario_name: 业务场景名称
            version: 版本号（如果为 None，返回最新版本）
            
        Returns:
            Dict[str, Any]: Scenario 信息，或 None
        """
        # 如果 version 为 None，查询最新版本（按 created_at 降序）
        # 查询 tag_scenario 表
        # 返回 scenario 信息
        pass
    
    def list_scenarios(
        self,
        include_legacy: bool = False
    ) -> List[Dict[str, Any]]:
        """
        列出所有 Scenarios
        
        Args:
            include_legacy: 是否包含遗留 scenarios
            
        Returns:
            List[Dict[str, Any]]: Scenario 列表
        """
        # 查询 tag_scenario 表
        # 如果 include_legacy = False，过滤掉 is_legacy = 1 的记录
        # 返回列表
        pass
    
    def mark_scenario_as_legacy(self, scenario_id: int):
        """
        标记 Scenario 为遗留
        
        Args:
            scenario_id: Scenario ID
        """
        # 更新 tag_scenario.is_legacy = 1
        # 同时标记该 scenario 下的所有 tag definitions 为 legacy
        pass
    
    def cleanup_old_versions(self, scenario_name: str, max_versions: int = 3) -> int:
        """
        清理旧的 legacy versions
        
        如果 legacy version 数量 >= max_versions，删除最老的
        
        Args:
            scenario_name: Scenario 名称
            max_versions: 最大保留的 legacy version 数量（默认 3，可配置）
            
        Returns:
            int: 删除的 scenario 数量
        """
        # 1. 查询所有 legacy scenarios（按 created_at 排序，最老的在前）
        #    legacy_scenarios = self.list_scenarios(
        #        scenario_name=scenario_name,
        #        include_legacy=True
        #    )
        #    legacy_scenarios = [s for s in legacy_scenarios if s["is_legacy"] == 1]
        #    legacy_scenarios.sort(key=lambda x: x["created_at"])
        # 
        # 2. 如果数量 >= max_versions：
        #    - 计算需要删除的数量：len(legacy_scenarios) - max_versions + 1
        #    - 删除最老的 scenarios（调用 delete_scenario）
        # 
        # 3. 返回删除的数量
        pass
    
    def delete_scenario(self, scenario_id: int, cascade: bool = True):
        """
        删除 Scenario（级联删除 tag definitions 和 tag values）
        
        Args:
            scenario_id: Scenario ID
            cascade: 是否级联删除（默认 True，删除 tag definitions 和 tag values）
        """
        # 1. 如果 cascade = True：
        #    - 删除该 scenario 的所有 tag values（通过 tag_value_model）
        #    - 删除该 scenario 的所有 tag definitions（通过 tag_definition_model）
        # 
        # 2. 删除 scenario（通过 tag_scenario_model）
        pass
    
    # ========================================================================
    # Tag Definition 操作
    # ========================================================================
    
    def create_tag_definition(
        self,
        scenario_id: int,
        scenario_version: str,
        name: str,
        display_name: str = None,
        description: str = ""
    ) -> int:
        """
        创建 Tag Definition
        
        Args:
            scenario_id: Scenario ID
            scenario_version: Scenario 版本号（冗余字段）
            name: 标签名称
            display_name: 显示名称（如果为 None，默认同 name）
            description: 描述
            
        Returns:
            int: Tag Definition ID
            
        Raises:
            ValueError: 如果 tag definition 已存在（scenario_id + name）
        """
        # 检查 tag definition 是否已存在（scenario_id + name）
        # 如果已存在，抛出 ValueError
        # 如果 display_name 为 None，使用 name
        # 插入 tag_definition 表（包含 scenario_version, is_legacy=0）
        # 返回 tag_definition_id
        pass
    
    def delete_tag_definitions_by_scenario(self, scenario_id: int):
        """
        删除 Scenario 下的所有 Tag Definitions
        
        Args:
            scenario_id: Scenario ID
        """
        # 删除 tag_definition 表中 scenario_id 匹配的所有记录
        pass
    
    def delete_tag_values_by_scenario(self, scenario_id: int):
        """
        删除 Scenario 下的所有 Tag Values
        
        Args:
            scenario_id: Scenario ID
        """
        # 1. 获取该 scenario 下的所有 tag definitions
        #    tag_definitions = self.get_tag_definitions(scenario_id=scenario_id)
        # 
        # 2. 对每个 tag definition：
        #    - 删除该 tag definition 的所有 tag values（通过 tag_value_model）
        pass
    
    def get_tag_definitions(
        self,
        scenario_id: int = None,
        scenario_name: str = None,
        version: str = None,
        include_legacy: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取 Tag Definitions
        
        Args:
            scenario_id: Scenario ID（优先使用）
            scenario_name: Scenario 名称
            version: 版本号
            include_legacy: 是否包含遗留 tags
            
        Returns:
            List[Dict[str, Any]]: Tag Definition 列表
        """
        # 如果 scenario_id 为 None，通过 scenario_name + version 查询 scenario_id
        # 查询 tag_definition 表
        # 如果 include_legacy = False，过滤掉 is_legacy = 1 的记录
        # 返回列表
        pass
    
    # ========================================================================
    # Tag Value 操作
    # ========================================================================
    
    def save_tag_value(
        self,
        tag_definition_id: int,
        entity_id: str,
        entity_type: str,
        as_of_date: str,
        value: str,
        start_date: str = None,
        end_date: str = None
    ):
        """
        保存 Tag Value
        
        Args:
            tag_definition_id: Tag Definition ID
            entity_id: 实体ID
            entity_type: 实体类型
            as_of_date: 业务日期
            value: 标签值（字符串）
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）
        """
        # 使用 tag_value_model 保存
        # 主键：(entity_id, tag_definition_id, as_of_date)
        # 如果已存在，更新；否则插入
        pass
    
    def get_tag_value(
        self,
        tag_definition_id: int,
        entity_id: str,
        as_of_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取 Tag Value
        
        Args:
            tag_definition_id: Tag Definition ID
            entity_id: 实体ID
            as_of_date: 业务日期
            
        Returns:
            Dict[str, Any]: Tag Value 信息，或 None
        """
        # 查询 tag_value 表
        # 返回结果
        pass
    
    def get_entity_tags(
        self,
        entity_id: str,
        as_of_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取某个实体在某个日期的所有 tags
        
        Args:
            entity_id: 实体ID
            as_of_date: 业务日期
            
        Returns:
            List[Dict[str, Any]]: Tag Value 列表
        """
        # 查询 tag_value 表
        # 返回列表
        pass
    
    def get_tag_value_model(self):
        """
        获取 TagValueModel 实例（供 Calculator 使用）
        
        Returns:
            TagValueModel 实例
        """
        # 返回 self.tag_value_model
        pass
```

---

## 4. DataManager 数据加载 API 伪代码

```python
# app/data_manager/data_manager.py 或 app/data_manager/data_services/...

class DataManager:
    """
    Data Manager - 数据管理器
    
    新增 Tag 计算所需的数据加载 API
    """
    
    # ========================================================================
    # Tag 计算所需的数据加载 API
    # ========================================================================
    
    def load_kline(
        self,
        entity_id: str,
        term: str,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        加载 K 线数据（用于 Tag 计算）
        
        Args:
            entity_id: 实体ID（如股票代码 "000001.SZ"）
            term: K 线周期（"daily", "weekly", "monthly"）
            start_date: 开始日期（格式：YYYYMMDD，可选）
            end_date: 结束日期（格式：YYYYMMDD，可选，如果为 None，使用最新日期）
            
        Returns:
            List[Dict[str, Any]]: K 线数据列表
                [
                    {
                        "date": "20250101",
                        "open": 10.0,
                        "high": 11.0,
                        "low": 9.0,
                        "close": 10.5,
                        "volume": 1000000,
                        ...
                    },
                    ...
                ]
        """
        # 1. 从数据库加载（使用对应的 kline model）
        # 2. 如果 start_date 为 None，从最早的数据开始
        # 3. 如果 end_date 为 None，使用最新交易日
        # 4. 过滤日期范围
        # 5. 按日期排序
        # 6. 返回列表
        pass
    
    def load_corporate_finance(
        self,
        entity_id: str,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        加载企业财务数据（用于 Tag 计算）
        
        Args:
            entity_id: 实体ID（如股票代码 "000001.SZ"）
            start_date: 开始日期（格式：YYYYMMDD，可选）
            end_date: 结束日期（格式：YYYYMMDD，可选）
            
        Returns:
            Dict[str, Any]: 财务数据字典
                {
                    "20250101": {
                        "roe": 0.15,
                        "roa": 0.08,
                        ...
                    },
                    ...
                }
        """
        # 1. 从数据库加载（使用 corporate_finance model）
        # 2. 如果 start_date 为 None，从最早的数据开始
        # 3. 如果 end_date 为 None，使用最新日期
        # 4. 过滤日期范围
        # 5. 按日期组织数据
        # 6. 返回字典
        pass
    
    def load_market_value(
        self,
        entity_id: str,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, float]:
        """
        加载市值数据（用于 Tag 计算）
        
        Args:
            entity_id: 实体ID（如股票代码 "000001.SZ"）
            start_date: 开始日期（格式：YYYYMMDD，可选）
            end_date: 结束日期（格式：YYYYMMDD，可选）
            
        Returns:
            Dict[str, float]: 市值数据字典
                {
                    "20250101": 1e10,
                    "20250102": 1.1e10,
                    ...
                }
        """
        # 1. 从数据库加载（使用对应的 model）
        # 2. 如果 start_date 为 None，从最早的数据开始
        # 3. 如果 end_date 为 None，使用最新日期
        # 4. 过滤日期范围
        # 5. 按日期组织数据
        # 6. 返回字典
        pass
    
    def get_tag_service(self) -> TagService:
        """
        获取 TagService 实例
        
        Returns:
            TagService 实例
        """
        # 返回 TagService 实例（单例或每次创建）
        pass
    
    # 可以根据需要添加更多数据源的 load 方法
    # 例如：load_index_data, load_macro_data 等
```

---

## 5. 使用流程伪代码

```python
# ========================================================================
# 1. 初始化 TagManager（自动发现和验证）
# ========================================================================
tag_manager = TagManager(data_mgr=data_manager)

# TagManager 自动完成：
# - 发现所有 scenarios（从配置的目录）
# - 加载 settings 和 calculators
# - 验证配置
# - 缓存 enable 的 calculators
# 注意：不在这里注册到数据库，延迟到 run() 时

# ========================================================================
# 2. 执行所有 Scenarios（入口函数）
# ========================================================================
tag_manager.run(data_source_mgr=data_source_manager)

# TagManager.run() 流程：
# 对每个 enable 的 scenario（同步执行）：
#   1. 获取 calculator 实例（自动创建并缓存）
#   2. 调用 calculator.run(data_source_mgr)
#   3. 等待完成（同步）
#   4. 如果出错，记录日志但继续执行其他 scenarios

# Calculator.run() 流程：
#   1. 检查 scenario 是否存在（通过 TagService）
#   2. 如果不存在：
#      - 创建 scenario 和 tag definitions（create 流程）
#      - 进入计算流程
#   3. 如果已存在：
#      - 对比 version
#      - 如果 version 相同：
#          * 按 update_mode 计算（renew 流程）
#      - 如果 version 不同：
#          * 根据 on_version_change 处理：
#            - NEW_SCENARIO: 创建新 scenario，标记旧的为 legacy，清理旧版本
#            - REFRESH_SCENARIO: 删除旧 tags，重新计算
#          * 进入计算流程

# 计算流程：
#   1. 确定计算日期范围（根据 update_mode）
#   2. 获取实体列表
#   3. 对每个实体：
#      a. 加载历史数据
#      b. 对每个 tag：
#          * 调用 calculate_tag()
#          * 保存 tag 值
#   4. 调用 on_finish()
```

---

## 6. 关键设计点

### 6.1 TagManager 职责
- **发现和加载**：发现所有 scenario calculators
- **自动注册**：发现 calculator 后自动检查数据库并注册 scenario 和 tag definitions
- **版本管理**：自动处理版本冲突（REFRESH_SCENARIO vs NEW_SCENARIO）
- **Calculator 管理**：自动创建和缓存 calculator 实例

### 6.2 BaseTagCalculator 职责
- **配置管理**：读取、验证、处理 settings
- **数据加载**：提供默认实现，支持扩展
- **计算执行**：调用用户实现的 calculate_tag
- **Tag 值保存**：通过 TagService 保存

### 6.3 DataManager TagService 职责
- **数据库操作**：Scenario、Tag Definition、Tag Value 的 CRUD 操作
- **数据查询**：提供各种查询接口
- **数据过滤**：支持 legacy 过滤等

### 6.4 DataManager 数据加载 API 职责
- **数据加载**：提供统一的数据加载接口（K线、财务、市值等）
- **日期范围处理**：支持 start_date 和 end_date
- **数据格式标准化**：返回标准化的数据格式

### 6.5 配置处理流程
1. **读取 settings**：动态导入 settings.py
2. **验证字段**：验证必需字段和枚举值
3. **应用默认值**：填充可选字段的默认值
4. **合并配置**：合并 calculator 和 tag 配置
5. **提取到实例变量**：方便访问

### 6.6 执行流程
1. **TagManager.run()**：循环执行每个 calculator.run()（同步）
2. **Calculator.run()**：
   - 检查 scenario 是否存在
   - 如果不存在：create 流程（创建 scenario 和 tags，然后计算）
   - 如果存在：renew 流程（对比 version，处理版本变更，然后计算）
3. **Version 变更处理**：
   - NEW_SCENARIO: 创建新 scenario，标记旧的为 legacy，清理旧版本（>= 3）
   - REFRESH_SCENARIO: 删除旧 tags，重新计算
4. **计算流程**：根据 update_mode 计算 tags

### 6.7 职责分离
- **TagManager**：发现、加载、自动注册、管理 calculator 实例
- **BaseTagCalculator**：配置处理、数据加载、计算执行
- **DataManager TagService**：所有数据库操作
- **DataManager**：数据加载 API（K线、财务等）

---

**文档结束**
