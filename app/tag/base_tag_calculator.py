"""
Tag Calculator 基类

职责：
1. 配置管理（读取、验证、处理）
2. 数据加载（钩子函数，默认实现支持股票）
3. 迭代逻辑（根据 base_term 迭代）
4. 计算钩子（calculate_tag，用户实现）
5. 其他钩子（初始化、清理、错误处理）
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import importlib.util
import os
import warnings
from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction


class BaseTagCalculator(ABC):
    """Tag Calculator 基类
    
    职责：
    1. 配置管理（读取、验证、处理）
    2. 数据加载（钩子函数，默认实现支持股票）
    3. 迭代逻辑（根据 base_term 迭代）
    4. 计算钩子（calculate_tag，用户实现）
    5. 其他钩子（初始化、清理、错误处理）
    """
    
    def __init__(
        self, 
        settings_path: str,
        data_mgr=None,
        tag_service=None
    ):
        """
        初始化 Calculator
        
        Args:
            settings_path: settings 文件路径（相对于 calculator 同级目录）
            data_mgr: DataManager 实例（用于访问数据库模型）
            tag_service: TagService 实例（用于访问 tag 相关的数据库操作）
        """
        self.settings_path = settings_path
        self.data_mgr = data_mgr
        self.tag_service = tag_service
        
        # 获取 calculator 文件路径（用于确定 settings 的相对路径）
        import inspect
        calculator_file = inspect.getfile(self.__class__)
        
        # 读取、验证和处理配置
        self.settings = self._load_and_process_settings(settings_path, calculator_file)
        
        # 提取 calculator 配置到实例变量
        self._extract_calculator_config()
        
        # 处理 tags 配置（合并、验证）
        self.tags_config = self._process_tags_config()
        
        # 初始化（钩子函数）
        self.on_init()
    
    # ========================================================================
    # 1. 配置管理（读取、验证、处理）
    # ========================================================================
    
    def _load_and_process_settings(
        self, 
        settings_path: str, 
        calculator_path: str
    ) -> Dict[str, Any]:
        """
        加载并处理 settings 文件
        
        注意：settings 文件存在性和 calculator 是否启用已在 TagManager 中检查
        这里只负责读取和验证配置结构
        
        Args:
            settings_path: settings 文件路径（相对路径）
            calculator_path: calculator 文件路径（用于确定相对路径的基准）
            
        Returns:
            Dict[str, Any]: 处理后的 settings 字典
            
        Raises:
            FileNotFoundError: 文件不存在（理论上不应该发生，因为 Manager 已检查）
            SyntaxError: 文件语法错误
            ValueError: 配置验证失败
            ImportError: 导入错误
        """
        # 1. 读取 settings 文件
        settings = self._read_settings_file(settings_path, calculator_path)
        
        # 2. 验证 calculator 必需字段（不再检查 is_enabled，Manager 已检查）
        self._validate_calculator_fields(settings)
        
        # 3. 处理 calculator 默认值
        self._apply_calculator_defaults(settings)
        
        # 4. 验证 calculator 枚举值
        self._validate_calculator_enums(settings)
        
        # 5. 验证 tags 配置
        self._validate_tags_fields(settings)
        
        return settings
    
    def _read_settings_file(
        self, 
        settings_path: str, 
        calculator_path: str
    ) -> Dict[str, Any]:
        """
        读取 settings 文件（Python 文件）
        
        注意：文件存在性已在 TagManager 中检查
        
        Args:
            settings_path: settings 文件路径（相对路径）
            calculator_path: calculator 文件路径（用于确定相对路径的基准）
            
        Returns:
            Dict[str, Any]: Settings 字典
            
        Raises:
            FileNotFoundError: 文件不存在（理论上不应该发生）
            SyntaxError: 文件语法错误
            ValueError: 缺少 Settings 变量
        """
        # 转换为绝对路径
        if not os.path.isabs(settings_path):
            # 相对于 calculator 同级目录
            calculator_dir = os.path.dirname(os.path.abspath(calculator_path))
            settings_path = os.path.join(calculator_dir, settings_path)
        
        # 注意：文件存在性检查已在 TagManager 中完成，这里不再检查
        # 但如果文件不存在，导入会失败，这是合理的
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("tag_settings", settings_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 settings 文件: {settings_path}")
        
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise SyntaxError(f"Settings 文件语法错误: {settings_path}\n{str(e)}")
        except Exception as e:
            raise ImportError(f"导入 settings 文件失败: {settings_path}\n{str(e)}")
        
        # 提取 Settings（注意：变量名是 Settings，不是 TAG_CONFIG）
        if not hasattr(module, "Settings"):
            raise ValueError(f"Settings 文件缺少 Settings 变量: {settings_path}")
        
        config = module.Settings
        
        if not isinstance(config, dict):
            raise ValueError(f"Settings 必须是字典类型，当前类型: {type(config)}")
        
        return config
    
    def _validate_calculator_fields(self, settings: Dict[str, Any]):
        """
        验证 calculator 必需字段
        
        Args:
            settings: settings 字典
            
        Raises:
            ValueError: 缺少必需字段或字段类型错误
        """
        if "calculator" not in settings:
            raise ValueError("配置缺少必需字段: calculator")
        
        calculator = settings["calculator"]
        
        # 验证 calculator.meta
        if "meta" not in calculator:
            raise ValueError("calculator 缺少必需字段: meta")
        
        calculator_meta = calculator["meta"]
        if not isinstance(calculator_meta, dict):
            raise ValueError(f"calculator.meta 必须是字典，当前类型: {type(calculator_meta)}")
        
        if "name" not in calculator_meta:
            raise ValueError("calculator.meta 缺少必需字段: name")
        
        if not isinstance(calculator_meta["name"], str):
            raise ValueError(f"calculator.meta.name 必须是字符串，当前类型: {type(calculator_meta['name'])}")
        
        # 验证 base_term
        if "base_term" not in calculator:
            raise ValueError("calculator 缺少必需字段: base_term")
        
        if not isinstance(calculator["base_term"], str):
            raise ValueError(f"calculator.base_term 必须是字符串，当前类型: {type(calculator['base_term'])}")
        
        # 验证 performance（必需字段）
        if "performance" not in calculator:
            raise ValueError("calculator 缺少必需字段: performance")
        
        perf = calculator["performance"]
        if not isinstance(perf, dict):
            raise ValueError(f"calculator.performance 必须是字典，当前类型: {type(perf)}")
    
    def _validate_tags_fields(self, settings: Dict[str, Any]):
        """
        验证 tags 配置
        
        Args:
            settings: settings 字典
            
        Raises:
            ValueError: tags 配置错误
        """
        if "tags" not in settings:
            raise ValueError("配置缺少必需字段: tags")
        
        tags = settings["tags"]
        if not isinstance(tags, list):
            raise ValueError(f"tags 必须是列表，当前类型: {type(tags)}")
        
        if len(tags) == 0:
            raise ValueError("tags 列表不能为空，至少需要一个 tag")
        
        # 验证每个 tag
        tag_names = set()
        for i, tag in enumerate(tags):
            if not isinstance(tag, dict):
                raise ValueError(f"tags[{i}] 必须是字典，当前类型: {type(tag)}")
            
            # 必需字段（注意：version 在 scenario 级别，不在 tag 级别）
            required_fields = ["name", "display_name"]
            for field in required_fields:
                if field not in tag:
                    raise ValueError(f"tags[{i}] 缺少必需字段: {field}")
            
            # 验证字段类型
            if not isinstance(tag["name"], str):
                raise ValueError(f"tags[{i}].name 必须是字符串，当前类型: {type(tag['name'])}")
            
            if not isinstance(tag["display_name"], str):
                raise ValueError(f"tags[{i}].display_name 必须是字符串，当前类型: {type(tag['display_name'])}")
            
            # 检查 tag name 唯一性
            tag_name = tag["name"]
            if tag_name in tag_names:
                raise ValueError(f"tags 中存在重复的 tag name: {tag_name}")
            tag_names.add(tag_name)
    
    def _apply_calculator_defaults(self, settings: Dict[str, Any]):
        """
        应用 calculator 默认值
        
        Args:
            settings: settings 字典（会被修改）
        """
        calculator = settings["calculator"]
        
        # core 默认 {}（如果不存在）
        if "core" not in calculator:
            calculator["core"] = {}
        
        # required_terms 默认 []
        if "required_terms" not in calculator or calculator["required_terms"] is None:
            calculator["required_terms"] = []
        
        # required_data 默认 []
        if "required_data" not in calculator:
            calculator["required_data"] = []
        
        # performance 默认值
        perf = calculator["performance"]
        # update_mode 和 on_version_change 是必需字段，不设置默认值
        # max_workers 是可选的，由系统根据 job 数量自动分配，不设置默认值
    
    def _validate_calculator_enums(self, settings: Dict[str, Any]):
        """
        验证 calculator 枚举值
        
        Args:
            settings: settings 字典
            
        Raises:
            ValueError: 枚举值无效
        """
        calculator = settings["calculator"]
        
        # 验证 base_term
        base_term = calculator["base_term"]
        valid_terms = [term.value for term in KlineTerm]
        if base_term not in valid_terms:
            raise ValueError(
                f"calculator.base_term 必须是 {valid_terms} 之一（使用 KlineTerm 枚举），"
                f"当前值: {base_term}"
            )
        
        # 验证 required_terms（如果存在）
        required_terms = calculator.get("required_terms", [])
        if required_terms:
            for term in required_terms:
                if term not in valid_terms:
                    raise ValueError(
                        f"calculator.required_terms 中的值必须是 {valid_terms} 之一（使用 KlineTerm 枚举），"
                        f"当前值: {term}"
                    )
        
        # 验证 performance 中的枚举值（如果存在）
        perf = calculator["performance"]
        
        # 验证 update_mode（如果存在）
        if "update_mode" in perf:
            update_mode = perf["update_mode"]
            valid_modes = [mode.value for mode in UpdateMode]
            if update_mode not in valid_modes:
                raise ValueError(
                    f"calculator.performance.update_mode 必须是 {valid_modes} 之一（使用 UpdateMode 枚举），"
                    f"当前值: {update_mode}"
                )
        
        # 验证 on_version_change（如果存在）
        if "on_version_change" in perf:
            on_version_change = perf["on_version_change"]
            valid_actions = [action.value for action in VersionChangeAction]
            if on_version_change not in valid_actions:
                raise ValueError(
                    f"calculator.performance.on_version_change 必须是 {valid_actions} 之一（使用 VersionChangeAction 枚举），"
                    f"当前值: {on_version_change}"
                )
    
    def _extract_calculator_config(self):
        """提取 calculator 配置到实例变量"""
        calculator = self.settings["calculator"]
        self.calculator_name = calculator["meta"]["name"]
        self.calculator_description = calculator["meta"].get("description", "")
        self.base_term = calculator["base_term"]
        self.required_terms = calculator.get("required_terms", [])
        self.required_data = calculator.get("required_data", [])
        self.calculator_core = calculator.get("core", {})
        self.calculator_performance = calculator.get("performance", {})
    
    def _process_tags_config(self) -> List[Dict[str, Any]]:
        """
        处理 tags 配置，合并 calculator 和 tag 配置
        
        Returns:
            List[Dict[str, Any]]: 处理后的 tags 配置列表（每个 tag 的配置已合并）
        """
        processed_tags = []
        
        for tag in self.settings["tags"]:
            # 注意：is_enabled 只在 calculator 级别，不在 tag 级别
            # 如果 calculator 启用，所有 tags 都会被处理
            
            # 合并配置
            merged_config = self._merge_tag_config(tag)
            processed_tags.append(merged_config)
        
        return processed_tags
    
    def _merge_tag_config(self, tag_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并 calculator 和 tag 配置
        
        注意：tag 级别不支持 core 和 performance，只在 calculator 级别配置
        
        Args:
            tag_config: tag 配置字典
            
        Returns:
            Dict[str, Any]: 合并后的配置
        """
        calculator = self.settings["calculator"]
        merged = calculator.copy()
        
        # 注意：tag 级别不支持 core 和 performance，直接使用 calculator 的配置
        # core 和 performance 只在 calculator 级别配置，所有 tags 共享
        
        # 添加 tag 元信息
        merged["tag_meta"] = {
            "name": tag_config["name"],
            "display_name": tag_config["display_name"],
            "description": tag_config.get("description", ""),
        }
        
        return merged
    
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
        加载实体历史数据（可扩展接口）
        
        默认实现：只支持股票，从数据库加载数据
        
        Tag 系统是预计算系统，数据应该已经存储在数据库中。
        所有数据都通过 DataManager 从数据库加载，不使用第三方数据源。
        
        高级用户扩展：
        - 重写此方法，支持其他 entity（指数、板块、kline 等）
        - 使用 self.data_mgr 从数据库加载自定义数据
        
        Args:
            entity_id: 实体ID（默认是股票代码）
            entity_type: 实体类型（默认 "stock"）
            as_of_date: 当前时间点（用于过滤历史数据，YYYYMMDD 格式）
            
        Returns:
            Dict[str, Any]: 历史数据字典
                - klines: Dict[str, List[Dict]] - K线数据，key 是 term（"daily", "weekly", "monthly"）
                - finance: List[Dict] - 财务数据（如果有）
                - ... 其他历史数据
        """
        if not self.data_mgr:
            raise ValueError("DataManager 未初始化，无法加载数据")
        
        historical_data = {}
        
        # 加载 kline 数据（根据 base_term 和 required_terms）
        kline_terms = set([self.base_term] + (self.required_terms or []))
        klines = {}
        
        for term in kline_terms:
            # 从数据库加载（通过 DataManager）
            kline_model = self.data_mgr.get_model(f"stock_kline_{term}")
            if kline_model:
                kline_data = kline_model.load_by_stock(entity_id, end_date=as_of_date)
                klines[term] = kline_data
        
        historical_data["klines"] = klines
        
        # 加载其他数据源
        for data_source in self.required_data:
            if data_source == "corporate_finance":
                finance_model = self.data_mgr.get_model("corporate_finance")
                if finance_model:
                    finance_data = finance_model.load_by_stock(entity_id, end_date=as_of_date)
                    historical_data["finance"] = finance_data
        
        return historical_data
    
    # ========================================================================
    # 3. 计算钩子（用户实现）
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
        
        钩子函数：为每个 tag 在每个时间点调用，用户实现计算逻辑
        
        Args:
            entity_id: 实体ID（如股票代码 "000001.SZ"）
            entity_type: 实体类型（如 "stock", "kline_daily" 等）
            as_of_date: 当前时间点（YYYYMMDD 格式，如 "20250101"）
            historical_data: 完整历史数据（上帝视角）
                - klines: Dict[str, List[Dict]] - K线数据，key 是 term
                - finance: List[Dict] - 财务数据（如果有）
                - ... 其他历史数据
            tag_config: 当前 tag 的配置（已合并 calculator 和 tag 配置）
                - base_term: 基础周期
                - required_terms: 需要的周期列表
                - required_data: 需要的数据源列表
                - core: calculator 的 core 参数（所有 tags 共享）
                - performance: calculator 的 performance 配置（所有 tags 共享）
                - tag_meta: tag 元信息（name, display_name, description）
                   注意：tag 级别不支持 core 和 performance，只在 calculator 级别配置
        
        Returns:
            TagEntity 或 None（不创建 tag）
        """
        pass
    
    # ========================================================================
    # 4. 其他钩子函数（可选实现）
    # ========================================================================
    
    def on_init(self):
        """
        初始化钩子（可选实现）
        
        在 Calculator 初始化后调用，用于：
        - 初始化缓存
        - 预加载数据
        - 其他初始化操作
        """
        pass
    
    def on_tag_created(self, tag_entity: Any, entity_id: str, as_of_date: str):
        """
        Tag 创建后钩子（可选实现）
        
        在 calculate_tag 返回 TagEntity 后调用，用于：
        - 记录日志
        - 更新缓存
        - 触发其他操作
        """
        pass
    
    def on_calculate_error(self, entity_id: str, as_of_date: str, error: Exception):
        """
        计算错误钩子（可选实现）
        
        在 calculate_tag 抛出异常时调用，用于：
        - 记录错误日志
        - 发送告警
        - 其他错误处理
        """
        # 默认实现：记录错误
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"计算 tag 失败: entity_id={entity_id}, as_of_date={as_of_date}, error={error}",
            exc_info=True
        )
    
    def should_continue_on_error(self) -> bool:
        """
        错误时是否继续（可选实现）
        
        返回 True 表示遇到错误时继续计算下一个时间点
        返回 False 表示遇到错误时中断计算
        
        默认：True（继续）
        """
        return True
    
    def on_finish(self, entity_id: str, tag_count: int):
        """
        完成钩子（可选实现）
        
        在单个实体计算完成后调用，用于：
        - 记录统计信息
        - 清理资源
        - 其他收尾操作
        """
        pass
