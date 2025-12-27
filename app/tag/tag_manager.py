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
- DataManager 是单例模式，内部自动获取
"""
from typing import Dict, List, Optional, Type, Any
import importlib.util
import logging
from pathlib import Path
from app.tag.base_tag_calculator import BaseTagCalculator
from app.tag.config import DEFAULT_SCENARIOS_ROOT
from app.tag.scenario_identifier import ScenarioIdentifier
from app.data_manager import DataManager
from utils.file.file_util import FileUtil

logger = logging.getLogger(__name__)


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
    
    def __init__(self):
        """
        初始化 TagManager
        
        DataManager 是单例模式，内部自动获取，不需要外部注入
        """
        # 从配置读取 scenarios 根目录（DEFAULT_SCENARIOS_ROOT）
        # 初始化字典：scenario 名称 -> scenario 信息字典
        # 每个 scenario 信息包含：
        #   - "calculator_class": Type[BaseTagCalculator]  # calculator 类
        #   - "settings": Dict[str, Any]  # settings 字典
        #   - "instance": Optional[BaseTagCalculator]  # calculator 实例（缓存，可能为 None）
        # 初始化 data_mgr（单例模式，内部自动获取）
        # 初始化 DataManager 的 tag 服务：
        #   - self.tag_service = data_mgr.get_tag_service()  # TagService（DataManager 提供）
        # 注意：不在这里发现 scenarios，延迟到 run() 时
        
        # 从配置读取 scenarios 根目录
        self.scenarios_root = Path(DEFAULT_SCENARIOS_ROOT)
        
        # 初始化字典：scenario 名称 -> scenario 信息字典
        # 每个 scenario 信息包含：
        #   - "calculator_class": Type[BaseTagCalculator]  # calculator 类
        #   - "settings": Dict[str, Any]  # settings 字典
        #   - "instance": Optional[BaseTagCalculator]  # calculator 实例（缓存，可能为 None）
        self.scenarios: Dict[str, Dict[str, Any]] = {}
        
        # 初始化 data_mgr（单例模式，内部自动获取）
        self.data_mgr = DataManager(is_verbose=False)
        
        # 初始化 DataManager 的 tag 服务
        self.tag_service = self.data_mgr.get_tag_service()  # TagService（DataManager 提供）
        
        # 注意：不在这里发现 scenarios，延迟到 run() 时
    
    def run(self):
        """
        执行所有 scenarios 的计算（入口函数）
        
        Tag 系统是预计算系统，数据应该从数据库（通过 DataManager）加载，
        不需要从第三方数据源（DataSourceManager）获取数据。
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
        #    b. 调用 calculator.run()
        #    c. 等待完成（同步）
        #    d. 如果出错，记录日志但继续执行其他 scenarios
        
        # 1. 发现所有 scenarios
        self._discover_and_register_calculators()
        
        # 2. 统一验证所有 settings
        self._validate_all_settings()
        
        # 3. 对每个 scenario（同步执行）
        for scenario_name in self.scenarios.keys():
            try:
                # 获取 calculator 实例（自动创建并缓存）
                calculator = self.get_calculator_instance(scenario_name)
                if calculator is None:
                    logger.warning(f"无法创建 calculator 实例: {scenario_name}，跳过")
                    continue
                
                # 调用 calculator.run()
                logger.info(f"开始执行 scenario: {scenario_name}")
                calculator.run()
                logger.info(f"完成执行 scenario: {scenario_name}")
                
            except Exception as e:
                # 如果出错，记录日志但继续执行其他 scenarios
                logger.error(
                    f"执行 scenario '{scenario_name}' 时出错: {e}",
                    exc_info=True
                )
                continue
    
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
        #   5. 检查 is_enabled 字段：
        #      - 如果没有，记录警告并跳过
        #      - 如果是 False，记录信息并跳过
        #      - 只有是 True 时才继续
        #   6. 加载 calculator 类（调用 _load_calculator）
        #   7. 存储到 self.scenarios 字典：scenario_name -> {
        #        "calculator_class": calculator_class,
        #        "settings": settings,
        #        "instance": None
        #    }
        #   注意：不在这里注册到数据库，延迟到 calculator.run() 时
        
        if not FileUtil.dir_exists(str(self.scenarios_root)):
            logger.warning(f"Scenarios 目录不存在: {self.scenarios_root}")
            return
        
        # 遍历 scenarios 目录下的所有子目录
        for scenario_dir in self.scenarios_root.iterdir():
            if not scenario_dir.is_dir():
                continue
            
            scenario_name = scenario_dir.name
            
            # 1. 检查 calculator.py 是否存在（递归查找）
            calculator_file_path = FileUtil.find_file_in_folder(
                "calculator.py",
                str(scenario_dir),
                is_recursively=True
            )
            if not calculator_file_path:
                logger.warning(
                    f"Scenario '{scenario_name}' 缺少 calculator.py 文件，跳过"
                )
                continue
            
            # 2. 检查 settings.py 是否存在（递归查找）
            settings_file_path = FileUtil.find_file_in_folder(
                "settings.py",
                str(scenario_dir),
                is_recursively=True
            )
            if not settings_file_path:
                logger.warning(
                    f"Scenario '{scenario_name}' 缺少 settings.py 文件，跳过"
                )
                continue
            
            # 3. 加载 settings（调用 _load_settings）
            try:
                settings = self._load_settings(Path(settings_file_path))
            except Exception as e:
                logger.warning(
                    f"加载 scenario '{scenario_name}' 的 settings 失败: {e}，跳过",
                    exc_info=True
                )
                continue
            
            # 3.5. 检查 is_enabled 字段
            if "is_enabled" not in settings:
                logger.warning(
                    f"Scenario '{scenario_name}' 缺少 'is_enabled' 字段，跳过"
                )
                continue
            
            if not settings.get("is_enabled", False):
                logger.info(
                    f"Scenario '{scenario_name}' 被禁用 (is_enabled=False)，跳过"
                )
                continue
            
            # 4. 加载 calculator 类（调用 _load_calculator）
            try:
                calculator_class = self._load_calculator(Path(calculator_file_path))
            except Exception as e:
                logger.warning(
                    f"加载 scenario '{scenario_name}' 的 calculator 失败: {e}，跳过",
                    exc_info=True
                )
                continue
            
            # 5. 存储到字典
            self.scenarios[scenario_name] = {
                "calculator_class": calculator_class,
                "settings": settings,
                "instance": None  # 实例缓存，延迟创建
            }
            
            # 创建 ScenarioIdentifier（用于日志和后续使用）
            scenario_id = ScenarioIdentifier.from_settings(settings)
            logger.info(f"发现 scenario: {scenario_id}")
    
    def _validate_all_settings(self):
        """
        统一验证所有 settings（schema 校验，抛出早期错误）
        """
        # 对每个 scenario 的 settings：
        #   1. 验证基本结构（scenario.name, scenario.version, calculator.base_term）
        #   2. 验证必需字段
        #   3. 验证枚举值（KlineTerm, UpdateMode, VersionChangeAction）
        #   4. 如果验证失败，抛出 ValueError 并记录详细的错误信息
        
        for scenario_name, scenario_info in self.scenarios.items():
            settings = scenario_info["settings"]
            try:
                # 1. 验证基本结构
                if not isinstance(settings, dict):
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings 必须是字典类型，当前类型: {type(settings)}"
                    )
                
                # 验证 scenario 部分并创建 ScenarioIdentifier
                if "scenario" not in settings:
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings 缺少 'scenario' 字段"
                    )
                scenario = settings["scenario"]
                if not isinstance(scenario, dict):
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings.scenario 必须是字典类型"
                    )
                if "name" not in scenario:
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings.scenario 缺少 'name' 字段"
                    )
                if "version" not in scenario:
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings.scenario 缺少 'version' 字段"
                    )
                
                # 创建 ScenarioIdentifier（用于后续验证和日志）
                scenario_id = ScenarioIdentifier.from_settings(settings)
                
                # 验证 calculator 部分
                if "calculator" not in settings:
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings 缺少 'calculator' 字段"
                    )
                calculator = settings["calculator"]
                if not isinstance(calculator, dict):
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings.calculator 必须是字典类型"
                    )
                if "base_term" not in calculator:
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings.calculator 缺少 'base_term' 字段"
                    )
                
                # 2. 验证必需字段（tags）
                if "tags" not in settings:
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings 缺少 'tags' 字段"
                    )
                tags = settings["tags"]
                if not isinstance(tags, list):
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings.tags 必须是列表类型"
                    )
                if len(tags) == 0:
                    raise ValueError(
                        f"Scenario '{scenario_name}': Settings.tags 至少需要包含一个 tag"
                    )
                
                # 3. 验证枚举值（这里可以添加更详细的验证）
                # 注意：详细的枚举值验证可以在 BaseTagCalculator 中完成
                
            except ValueError as e:
                # 如果验证失败，抛出 ValueError 并记录详细的错误信息
                logger.error(f"验证 scenario '{scenario_name}' 的 settings 失败: {e}")
                raise
            except Exception as e:
                # 其他异常（如 ScenarioIdentifier 创建失败）
                logger.error(f"验证 scenario '{scenario_name}' 的 settings 时发生异常: {e}")
                raise
    
    def register_scenario(self, settings_dict: Dict[str, Any]):
        """
        手动注册 scenario（支持"无 settings 文件"的入口）
        
        未来实现：允许用户传入 settings 字典，创建"隐形"的 tag 计算器
        
        Args:
            settings_dict: Settings 字典（格式同 settings.py 中的 Settings）
        """
        # 1. 验证 settings_dict（调用 _validate_settings）
        # 2. 创建 calculator 实例（从 settings_dict 创建，没有 settings 文件）
        # 3. 调用 calculator.run()
        # 注意：这是未来功能，当前可以先不实现
        
        # TODO: 未来实现
        raise NotImplementedError("register_scenario 功能尚未实现")
    
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
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("tag_settings", settings_file)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 settings 文件: {settings_file}")
        
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise ValueError(f"Settings 文件语法错误: {settings_file}\n{str(e)}")
        except Exception as e:
            raise ValueError(f"导入 settings 文件失败: {settings_file}\n{str(e)}")
        
        # 提取 Settings 变量
        if not hasattr(module, "Settings"):
            raise ValueError(f"Settings 文件缺少 Settings 变量: {settings_file}")
        
        settings = module.Settings
        
        # 验证 Settings 是字典类型
        if not isinstance(settings, dict):
            raise ValueError(
                f"Settings 必须是字典类型，当前类型: {type(settings)}"
            )
        
        # 验证必需字段：scenario.name, scenario.version, calculator.base_term
        if "scenario" not in settings:
            raise ValueError("Settings 缺少 'scenario' 字段")
        if "name" not in settings["scenario"]:
            raise ValueError("Settings.scenario 缺少 'name' 字段")
        if "version" not in settings["scenario"]:
            raise ValueError("Settings.scenario 缺少 'version' 字段")
        
        if "calculator" not in settings:
            raise ValueError("Settings 缺少 'calculator' 字段")
        if "base_term" not in settings["calculator"]:
            raise ValueError("Settings.calculator 缺少 'base_term' 字段")
        
        return settings
    
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
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("tag_calculator", calculator_file)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 calculator 文件: {calculator_file}")
        
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise ValueError(f"Calculator 文件语法错误: {calculator_file}\n{str(e)}")
        except Exception as e:
            raise ValueError(f"导入 calculator 文件失败: {calculator_file}\n{str(e)}")
        
        # 查找继承自 BaseTagCalculator 的类
        calculator_class = None
        for name, obj in module.__dict__.items():
            if (isinstance(obj, type) and 
                issubclass(obj, BaseTagCalculator) and 
                obj != BaseTagCalculator):
                calculator_class = obj
                break
        
        if calculator_class is None:
            raise ValueError(
                f"Calculator 文件中没有找到继承自 BaseTagCalculator 的类: {calculator_file}"
            )
        
        return calculator_class
    
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
        scenario_info = self.scenarios.get(scenario_name)
        if scenario_info:
            return scenario_info.get("calculator_class")
        return None
    
    def get_calculator_instance(
        self,
        scenario_name: str
    ) -> Optional[BaseTagCalculator]:
        """
        获取指定 scenario 的 calculator 实例（自动创建并缓存）
        
        TagManager 自动管理 calculator 实例的创建和缓存
        
        Args:
            scenario_name: scenario 名称（目录名）
            
        Returns:
            BaseTagCalculator 实例或 None
        """
        # 1. 获取 scenario 信息
        # 2. 检查缓存（scenario_info["instance"]）
        # 3. 如果已缓存，直接返回
        # 4. 如果未缓存：
        #    - 获取 calculator 类和 settings
        #    - 确定 settings 文件路径
        #    - 创建 calculator 实例：
        #        * settings_path
        #        * data_mgr=self.data_mgr
        #        * tag_service=self.tag_service
        #    - 缓存到 scenario_info["instance"]
        #    - 返回实例
        
        # 1. 获取 scenario 信息
        scenario_info = self.scenarios.get(scenario_name)
        if scenario_info is None:
            return None
        
        # 2. 检查缓存
        if scenario_info["instance"] is not None:
            return scenario_info["instance"]
        
        # 3. 获取 calculator 类和 settings
        calculator_class = scenario_info["calculator_class"]
        settings = scenario_info["settings"]
        
        # 4. 确定 settings 文件路径
        # 注意：这里需要找到实际的 settings 文件路径
        # 由于我们在 _discover_and_register_calculators 中已经加载了 settings
        # 这里可以使用相对路径或绝对路径
        # 为了简化，我们使用相对路径（相对于 scenario 目录）
        settings_path = "settings.py"  # 相对于 calculator 同级目录
        
        # 5. 创建 calculator 实例
        try:
            calculator = calculator_class(
                settings_path=settings_path,
                data_mgr=self.data_mgr,
                tag_service=self.tag_service
            )
            
            # 6. 缓存到 scenario_info
            scenario_info["instance"] = calculator
            
            return calculator
        except Exception as e:
            logger.error(
                f"创建 calculator 实例失败: {scenario_name}, 错误: {e}",
                exc_info=True
            )
            return None
    
    def list_scenarios(self) -> List[str]:
        """
        列出所有可用的 scenario 名称
        
        Returns:
            List[str]: scenario 名称列表
        """
        # 返回 self.scenarios 字典的所有键
        return list(self.scenarios.keys())
    
    def reload(self):
        """
        重新发现所有 scenarios
        
        用于动态加载新添加的 scenario
        """
        # 清空字典
        # 调用 _discover_and_register_calculators()
        
        self.scenarios.clear()
        self._discover_and_register_calculators()
