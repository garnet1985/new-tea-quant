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
    
    def run(self, scenario_name: str = None):
        """
        执行 scenarios 的计算（入口函数）
        
        Tag 系统是预计算系统，数据应该从数据库（通过 DataManager）加载，
        不需要从第三方数据源（DataSourceManager）获取数据。
        
        Args:
            scenario_name: 可选，如果提供则只执行指定的 scenario，否则执行所有 scenarios
        """
        # 1. 发现和验证所有 scenarios（调用 _discover_and_validate_scenarios）
        #    - 发现所有 scenarios
        #    - 验证所有 settings
        #    - 移除验证失败的 scenarios
        # 
        # 2. 执行 scenarios：
        #    - 如果 scenario_name 为 None，执行所有 scenarios
        #    - 如果 scenario_name 不为 None，只执行指定的 scenario
        #    - 对每个 scenario：
        #        a. 获取 calculator 实例（自动创建并缓存）
        #        b. 调用 calculator.run()
        #        c. 等待完成（同步）
        #        d. 如果出错，记录日志但继续执行其他 scenarios
        
        # 1. 发现和验证所有 scenarios
        self._discover_and_validate_scenarios()
        
        # 2. 确定要执行的 scenarios
        if scenario_name is not None:
            if scenario_name not in self.scenarios:
                raise ValueError(
                    f"Scenario '{scenario_name}' 不存在或验证失败。"
                    f"可用的 scenarios: {list(self.scenarios.keys())}"
                )
            scenarios_to_run = [scenario_name]
        else:
            scenarios_to_run = list(self.scenarios.keys())
        
        if len(scenarios_to_run) == 0:
            logger.warning("没有可用的 scenarios 需要执行")
            return
        
        # 3. 执行 scenarios
        for scenario_name in scenarios_to_run:
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
    
    def _discover_and_validate_scenarios(self):
        """
        发现和验证所有 scenarios
        
        统一入口：完成发现、注册、验证，并移除验证失败的 scenarios
        
        确保 self.scenarios 中只包含验证通过的可用 scenarios
        """
        # 1. 发现所有 scenarios（调用 _discover_and_register_calculators）
        # 2. 验证所有 settings，移除验证失败的（调用 _validate_all_settings_and_remove_invalid）
        
        # 1. 发现所有 scenarios
        self._discover_and_register_calculators()
        
        # 2. 验证所有 settings，移除验证失败的
        self._validate_all_settings_and_remove_invalid()
        
        # 确保 scenarios 中只包含验证通过的可用 scenarios
        logger.info(f"发现并验证完成，共有 {len(self.scenarios)} 个可用的 scenarios")
    
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
        #   6. 调用统一的注册入口（register_scenario）
        #      - register_scenario 会检查 is_enabled 字段
        #      - register_scenario 会验证 settings 结构
        #      - register_scenario 会存储到字典
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
            
            # 4. 加载 calculator 类（调用 _load_calculator）
            try:
                calculator_class = self._load_calculator(Path(calculator_file_path))
            except Exception as e:
                logger.warning(
                    f"加载 scenario '{scenario_name}' 的 calculator 失败: {e}，跳过",
                    exc_info=True
                )
                continue
            
            # 5. 调用统一的注册入口（register_scenario）
            try:
                self.register_scenario(
                    calculator_class=calculator_class,
                    settings_dict=settings,
                    scenario_name=scenario_name
                )
            except ValueError as e:
                # 验证失败，记录警告并跳过（不会添加到 scenarios 中）
                logger.warning(
                    f"注册 scenario '{scenario_name}' 失败: {e}，跳过"
                )
                continue
            except Exception as e:
                # 其他异常，记录错误并跳过（不会添加到 scenarios 中）
                logger.error(
                    f"注册 scenario '{scenario_name}' 时发生异常: {e}，跳过",
                    exc_info=True
                )
                continue
    
    def _validate_all_settings_and_remove_invalid(self):
        """
        验证所有已注册 scenarios 的 settings，并移除验证失败的
        
        注意：基本结构验证已在 register_scenario 中完成，这里主要做额外的验证
        （如枚举值验证等）
        
        验证失败的 scenarios 会被从 self.scenarios 中移除
        """
        # 对每个已注册的 scenario：
        #   1. 验证枚举值（KlineTerm, UpdateMode, VersionChangeAction）
        #   2. 其他高级验证
        #   3. 如果验证失败，从 self.scenarios 中移除并记录错误
        
        invalid_scenarios = []
        
        for scenario_name, scenario_info in list(self.scenarios.items()):
            settings = scenario_info["settings"]
            try:
                # 创建 ScenarioIdentifier（用于日志）
                scenario_id = ScenarioIdentifier.from_settings(settings)
                
                # 验证枚举值（这里可以添加更详细的验证）
                # 注意：详细的枚举值验证可以在 BaseTagCalculator 中完成
                # 例如：验证 base_term 是否在 KlineTerm 枚举中
                # 例如：验证 update_mode 是否在 UpdateMode 枚举中
                # 例如：验证 on_version_change 是否在 VersionChangeAction 枚举中
                
            except ValueError as e:
                # 如果验证失败，记录错误并标记为无效
                logger.error(f"验证 scenario '{scenario_name}' 的 settings 失败: {e}")
                invalid_scenarios.append(scenario_name)
            except Exception as e:
                # 其他异常（如 ScenarioIdentifier 创建失败）
                logger.error(f"验证 scenario '{scenario_name}' 的 settings 时发生异常: {e}")
                invalid_scenarios.append(scenario_name)
        
        # 移除验证失败的 scenarios
        for scenario_name in invalid_scenarios:
            del self.scenarios[scenario_name]
            logger.warning(f"已移除验证失败的 scenario: {scenario_name}")
    
    def register_scenario(
        self, 
        calculator_class: Type[BaseTagCalculator], 
        settings_dict: Dict[str, Any],
        scenario_name: str = None
    ):
        """
        注册 scenario（统一入口）
        
        这是统一的注册入口，内部函数和外部 API 都调用此方法。
        完成所有验证和存储逻辑。
        
        Args:
            calculator_class: Calculator 类（继承自 BaseTagCalculator）
            settings_dict: Settings 字典（格式同 settings.py 中的 Settings）
            scenario_name: Scenario 名称（可选，如果不提供，从 settings.scenario.name 获取）
            
        Raises:
            ValueError: 如果验证失败
            
        Note:
            - 如果 is_enabled=False，会记录信息并返回（不抛出异常）
            - 其他验证失败会抛出 ValueError
        """
        # 1. 验证 settings 基本结构
        if not isinstance(settings_dict, dict):
            raise ValueError(f"Settings 必须是字典类型，当前类型: {type(settings_dict)}")
        
        # 2. 获取 scenario_name（从参数或 settings 中获取）
        if scenario_name is None:
            if "scenario" not in settings_dict:
                raise ValueError("Settings 缺少 'scenario' 字段，无法获取 scenario_name")
            scenario = settings_dict["scenario"]
            if not isinstance(scenario, dict) or "name" not in scenario:
                raise ValueError("Settings.scenario 缺少 'name' 字段，无法获取 scenario_name")
            scenario_name = scenario["name"]
        
        # 3. 检查 is_enabled 字段
        if "is_enabled" not in settings_dict:
            raise ValueError(f"Scenario '{scenario_name}' 缺少 'is_enabled' 字段")
        
        if not settings_dict.get("is_enabled", False):
            logger.info(f"Scenario '{scenario_name}' 被禁用 (is_enabled=False)，跳过注册")
            return  # 不抛出异常，只是跳过
        
        # 4. 验证 settings 结构（调用 _validate_settings_structure）
        self._validate_settings_structure(scenario_name, settings_dict)
        
        # 5. 存储到字典
        self.scenarios[scenario_name] = {
            "calculator_class": calculator_class,
            "settings": settings_dict,
            "instance": None  # 实例缓存，延迟创建
        }
        
        # 创建 ScenarioIdentifier（用于日志和后续使用）
        scenario_id = ScenarioIdentifier.from_settings(settings_dict)
        logger.info(f"注册 scenario: {scenario_id}")
    
    def _validate_settings_structure(self, scenario_name: str, settings: Dict[str, Any]):
        """
        验证 settings 结构（不包含 is_enabled 检查，因为已在 register_scenario 中检查）
        
        Args:
            scenario_name: Scenario 名称（用于错误信息）
            settings: Settings 字典
            
        Raises:
            ValueError: 如果验证失败
        """
        # 验证 scenario 部分
        if "scenario" not in settings:
            raise ValueError(f"Scenario '{scenario_name}': Settings 缺少 'scenario' 字段")
        scenario = settings["scenario"]
        if not isinstance(scenario, dict):
            raise ValueError(f"Scenario '{scenario_name}': Settings.scenario 必须是字典类型")
        if "name" not in scenario:
            raise ValueError(f"Scenario '{scenario_name}': Settings.scenario 缺少 'name' 字段")
        if "version" not in scenario:
            raise ValueError(f"Scenario '{scenario_name}': Settings.scenario 缺少 'version' 字段")
        
        # 验证 calculator 部分
        if "calculator" not in settings:
            raise ValueError(f"Scenario '{scenario_name}': Settings 缺少 'calculator' 字段")
        calculator = settings["calculator"]
        if not isinstance(calculator, dict):
            raise ValueError(f"Scenario '{scenario_name}': Settings.calculator 必须是字典类型")
        if "base_term" not in calculator:
            raise ValueError(f"Scenario '{scenario_name}': Settings.calculator 缺少 'base_term' 字段")
        
        # 验证 tags 部分
        if "tags" not in settings:
            raise ValueError(f"Scenario '{scenario_name}': Settings 缺少 'tags' 字段")
        tags = settings["tags"]
        if not isinstance(tags, list):
            raise ValueError(f"Scenario '{scenario_name}': Settings.tags 必须是列表类型")
        if len(tags) == 0:
            raise ValueError(f"Scenario '{scenario_name}': Settings.tags 至少需要包含一个 tag")
    
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
