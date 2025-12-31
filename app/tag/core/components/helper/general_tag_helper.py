import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import importlib.util
import logging

from app.tag.core.base_tag_worker import BaseTagWorker
from app.tag.core.components.settings_management.setting_manager import SettingsManager
from app.tag.core.config import DEFAULT_SCENARIOS_ROOT
from utils.file.file_util import FileUtil

logger = logging.getLogger(__name__)
class GeneralTagHelper:
    """
    General Tag Helper

    职责：
    1. 发现和加载可执行的 scenarios（文件扫描 + settings 验证）
    """

    # -------------------------------------------------------------------------
    # Scenario 发现与加载
    # -------------------------------------------------------------------------

    @staticmethod
    def load_scenarios() -> List[Dict[str, Any]]:
        """
        加载所有可执行的 scenarios（扫描、加载、验证、过滤）
        
        流程：
        1. 遍历 scenarios_root 目录
        2. 对每个 scenario 目录调用 _load_and_validate_single_scenario
        3. 检查是否有重复的 scenario name
        4. 返回标准化的 scenario_info 列表
        
        Returns:
            List[Dict[str, Any]]: 标准化的 scenario_info 列表，每个元素包含：
                - "scenario_name": str - scenario 名称
                - "settings": Dict[str, Any] - settings 字典
                - "worker_class": type[BaseTagWorker] - worker 类
        """
        scenarios_root = Path(DEFAULT_SCENARIOS_ROOT)
        executable_scenarios: List[Dict[str, Any]] = []

        if not FileUtil.dir_exists(str(scenarios_root)):
            logger.warning(f"Scenarios 目录不存在: {scenarios_root}")
            return executable_scenarios

        for scenario_dir in scenarios_root.iterdir():
            if not scenario_dir.is_dir():
                continue

            scenario_info = GeneralTagHelper._load_and_validate_single_scenario(
                scenario_dir=scenario_dir,
                target_scenario_name=None,
                include_worker_class=True  # 统一包含 worker_class
            )
            
            if scenario_info:
                # 标准化 scenario_info 结构
                standardized_info = GeneralTagHelper._standardize_scenario_info(scenario_info)
                executable_scenarios.append(standardized_info)

        # 检查是否有重复的 scenario name
        duplicated_names = GeneralTagHelper.find_duplicated_scenario_names(executable_scenarios)
        if duplicated_names:
            error_msg = f"发现重复的 scenario name: {', '.join(set(duplicated_names))}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"共加载 {len(executable_scenarios)} 个可执行的 scenarios")
        return executable_scenarios

    @staticmethod
    def _standardize_scenario_info(scenario_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化 scenario_info 结构
        
        标准化的 scenario_info 包含 execute 所需的所有信息：
        - scenario_name: str - scenario 名称
        - settings: Dict[str, Any] - settings 字典
        - worker_class: type[BaseTagWorker] - worker 类
        
        Args:
            scenario_info: 从 _load_and_validate_single_scenario 返回的原始 scenario_info
        
        Returns:
            Dict[str, Any]: 标准化的 scenario_info
        """
        # 统一使用 scenario_name
        scenario_name = scenario_info.get("scenario_name")
        if not scenario_name:
            raise ValueError("scenario_info 缺少 scenario_name 字段")
        
        # 确保 worker_class 存在
        worker_class = scenario_info.get("worker_class")
        if not worker_class:
            raise ValueError(f"scenario_info 缺少 worker_class 字段: {scenario_name}")
        
        return {
            "scenario_name": scenario_name,
            "settings": scenario_info["settings"],
            "worker_class": worker_class,
        }

    @staticmethod
    def load_scenario_by_name(scenario_name: str) -> Optional[Dict[str, Any]]:
        """
        根据 scenario_name 加载 scenario 设置
        
        流程：
        1. 遍历 scenarios_root 目录
        2. 对每个 scenario 目录调用 _load_and_validate_single_scenario（指定 target_scenario_name）
        3. 返回标准化的 scenario_info
        
        Args:
            scenario_name: Scenario 名称
            
        Returns:
            Optional[Dict[str, Any]]: 标准化的 scenario_info，包含：
                - "scenario_name": str - scenario 名称
                - "settings": Dict[str, Any] - settings 字典
                - "worker_class": type[BaseTagWorker] - worker 类
            如果找不到或验证失败返回 None
        """
        scenarios_root = Path(DEFAULT_SCENARIOS_ROOT)

        if not FileUtil.dir_exists(str(scenarios_root)):
            logger.warning(f"Scenarios 目录不存在: {scenarios_root}")
            return None

        for scenario_dir in scenarios_root.iterdir():
            if not scenario_dir.is_dir():
                continue

            scenario_info = GeneralTagHelper._load_and_validate_single_scenario(
                scenario_dir=scenario_dir,
                target_scenario_name=scenario_name,
                include_worker_class=True
            )
            
            if scenario_info:
                # 标准化 scenario_info 结构
                return GeneralTagHelper._standardize_scenario_info(scenario_info)

        return None

    @staticmethod
    def is_scenario_settings_file_exists(scenario_dir: Path) -> bool:
        """
        验证 scenario 文件是否有效
        
        检查：
        1. 是否有 settings.py
        2. settings 是否有唯一的 name
        3. is_enabled 是否为 True
        
        Args:
            scenario_dir: Scenario 目录路径
            
        Returns:
            bool: 如果有效返回 True，否则返回 False
        """
        settings_file_path = SettingsManager.load_scenario_settings(scenario_dir)
        if not settings_file_path:
            return False
        
        # 验证 settings 内容（name 和 is_enabled）
        return GeneralTagHelper.validate_settings_file_and_content(settings_file_path)

    @staticmethod
    def validate_settings_file_and_content(settings_file_path: Path) -> bool:
        """
        验证 settings.py 文件内容是否有效
        
        检查：
        1. settings 是否有唯一的 name
        2. is_enabled 是否为 True
        
        Args:
            settings_file_path: settings.py 文件路径
            
        Returns:
            bool: 如果有效返回 True，否则返回 False
        """
        try:
            settings = SettingsManager.load_settings_from_file(str(settings_file_path))
            
            # 检查是否有 name 字段
            scenario_name = settings.get("scenario", {}).get("name")
            if not scenario_name:
                logger.warning(f"Settings 文件缺少 scenario.name 字段: {settings_file_path}")
                return False
            
            # 检查 is_enabled
            if not settings.get("is_enabled", False):
                logger.debug(f"Scenario '{scenario_name}' 被禁用 (is_enabled=False)")
                return False
            
            return True
        except Exception as e:
            logger.warning(
                f"验证 settings 文件失败: {settings_file_path}, 错误: {e}",
                exc_info=True
            )
            return False

    @staticmethod
    def validate_tag_worker_file_and_content(tag_worker_file_path: Path) -> Optional[type[BaseTagWorker]]:
        """
        验证 tag_worker.py 文件是否有效，并返回 worker 类
        
        检查：
        1. 文件是否存在
        2. worker 类是否继承自 BaseTagWorker
        
        Args:
            tag_worker_file_path: tag_worker.py 文件路径
            
        Returns:
            Optional[type[BaseTagWorker]]: 如果有效返回 worker 类，否则返回 None
        """
        try:
            spec = importlib.util.spec_from_file_location("tag_worker", tag_worker_file_path)
            if spec is None or spec.loader is None:
                logger.warning(f"无法加载 worker 文件: {tag_worker_file_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except SyntaxError as e:
                logger.warning(f"Worker 文件语法错误: {tag_worker_file_path}\n{str(e)}")
                return None
            except Exception as e:
                logger.warning(f"导入 worker 文件失败: {tag_worker_file_path}\n{str(e)}")
                return None

            worker_class = None
            for name, obj in module.__dict__.items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseTagWorker)
                    and obj is not BaseTagWorker
                ):
                    worker_class = obj
                    break

            if worker_class is None:
                logger.warning(
                    f"Worker 文件中没有找到继承自 BaseTagWorker 的类: {tag_worker_file_path}"
                )
                return None

            return worker_class
        except Exception as e:
            logger.warning(
                f"验证 tag_worker 文件失败: {tag_worker_file_path}, 错误: {e}",
                exc_info=True
            )
            return None

    @staticmethod
    def _load_and_validate_single_scenario(
        scenario_dir: Path,
        target_scenario_name: Optional[str] = None,
        include_worker_class: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        加载并验证单个 scenario（公共方法）
        
        流程：
        1. 检查是否有 settings.py（is_scenario_settings_file_exists）
        2. 验证 settings 内容（validate_settings_file_and_content）
        3. 如果指定了 target_scenario_name，检查 scenario_name 是否匹配
        4. 检查是否有 tag_worker.py
        5. 验证 tag_worker 内容（validate_tag_worker_file_and_content）
        6. 验证 settings 结构（SettingsManager.validate_settings）
        
        Args:
            scenario_dir: Scenario 目录路径
            target_scenario_name: 目标 scenario 名称（可选，如果指定则只加载匹配的）
            include_worker_class: 是否在返回结果中包含 worker_class 和文件路径
        
        Returns:
            Optional[Dict[str, Any]]: Scenario 信息，包含：
                - "scenario_name": str - scenario 名称
                - "settings": Dict[str, Any] - settings 字典
                - "worker_class": type[BaseTagWorker] (可选) - worker 类
                - "worker_file_path": str (可选) - worker 文件路径
                - "settings_file_path": str (可选) - settings 文件路径
            如果验证失败或 scenario_name 不匹配返回 None
        """
        # 1. 检查是否有 settings.py
        if not GeneralTagHelper.is_scenario_settings_file_exists(scenario_dir):
            logger.debug(f"Scenario '{scenario_dir.name}' 缺少 settings.py 文件或验证失败，跳过")
            return None

        settings_file_path = SettingsManager.load_scenario_settings(scenario_dir)
        if not settings_file_path:
            return None

        # 2. 验证 settings 内容（name 和 is_enabled）
        if not GeneralTagHelper.validate_settings_file_and_content(settings_file_path):
            return None

        # 3. 加载 settings
        try:
            settings = SettingsManager.load_settings_from_file(str(settings_file_path))
        except Exception as e:
            logger.warning(
                f"加载 scenario '{scenario_dir.name}' 的 settings 失败: {e}",
                exc_info=True
            )
            return None

        scenario_name = settings.get("scenario", {}).get("name")
        if not scenario_name:
            logger.warning(f"Scenario '{scenario_dir.name}' 缺少 name 字段，跳过")
            return None

        # 4. 如果指定了 target_scenario_name，检查是否匹配
        if target_scenario_name is not None and scenario_name != target_scenario_name:
            return None

        # 5. 检查是否有 tag_worker.py
        tag_worker_file_path = FileUtil.find_file_in_folder(
            "tag_worker.py",
            str(scenario_dir),
            is_recursively=True,
        )
        if not tag_worker_file_path:
            logger.warning(f"Scenario '{scenario_name}' 缺少 tag_worker.py 文件")
            return None

        # 6. 验证 tag_worker 内容（是否继承自 BaseTagWorker）
        worker_class = GeneralTagHelper.validate_tag_worker_file_and_content(Path(tag_worker_file_path))
        if not worker_class:
            logger.warning(f"Scenario '{scenario_name}' 的 tag_worker 验证失败")
            return None

        # 7. 验证 settings 结构（完整验证）
        try:
            SettingsManager.validate_settings(settings)
        except ValueError as e:
            logger.warning(
                f"Scenario '{scenario_name}' 的 settings 结构验证失败: {e}"
            )
            return None

        # 8. 构建返回结果（统一使用 scenario_name）
        result = {
            "scenario_name": scenario_name,
            "settings": settings,
        }
        
        if include_worker_class:
            result["worker_class"] = worker_class
            result["worker_file_path"] = tag_worker_file_path
            result["settings_file_path"] = str(settings_file_path)

        return result

    @staticmethod
    def find_duplicated_scenario_names(scenarios: List[Dict[str, Any]]) -> List[str]:
        """
        检查 scenarios 中是否有重复的 scenario name
        
        Args:
            scenarios: 标准化的 scenario_info 列表（必须包含 scenario_name 字段）
        
        Returns:
            List[str]: 重复的 scenario_name 列表
        """
        duplicated_names = []
        scenario_names = [scenario["scenario_name"] for scenario in scenarios]
        if len(scenario_names) != len(set(scenario_names)):
            duplicated_names = [name for name in scenario_names if scenario_names.count(name) > 1]
        return duplicated_names