from typing import Dict, List, Any, Optional
from pathlib import Path
import importlib.util
import logging

from app.tag.core.base_tag_worker import BaseTagWorker
from app.tag.core.components.settings_management.setting_manager import SettingsManager
from utils.file.file_util import FileUtil


logger = logging.getLogger(__name__)


class GeneralTagHelper:
    """
    General Tag Helper

    职责：
    1. 发现和加载可执行的 scenarios（文件扫描 + settings 验证）
    2. 决定多进程 worker 数量
    """

    # -------------------------------------------------------------------------
    # 多进程 worker 数量决策
    # -------------------------------------------------------------------------

    @staticmethod
    def decide_worker_amount(jobs: List[Dict[str, Any]]) -> int:
        """
        根据 job 数量决定进程数（最多10个）

        策略：
        1. 如果 job 数量 <= 1，使用1个进程
        2. 如果 job 数量 <= 5，使用2个进程
        3. 如果 job 数量 <= 10，使用3个进程
        4. 如果 job 数量 <= 20，使用5个进程
        5. 如果 job 数量 <= 50，使用8个进程
        6. 否则使用10个进程（最大）
        """
        job_count = len(jobs)

        if job_count <= 1:
            return 1
        elif job_count <= 5:
            return 2
        elif job_count <= 10:
            return 3
        elif job_count <= 20:
            return 5
        elif job_count <= 50:
            return 8
        else:
            return 10  # 最大10个进程

    # -------------------------------------------------------------------------
    # Scenario 发现与加载
    # -------------------------------------------------------------------------

    @staticmethod
    def load_executable_scenarios(
        scenarios_root: Path,
        is_verbose: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        加载所有可执行的 scenarios（扫描、加载、验证、过滤）

        Args:
            scenarios_root: scenarios 根目录
            is_verbose: 是否输出详细日志

        Returns:
            List[Dict[str, Any]]: 可执行的 scenario 信息列表
        """
        executable_scenarios: List[Dict[str, Any]] = []

        if not FileUtil.dir_exists(str(scenarios_root)):
            logger.warning(f"Scenarios 目录不存在: {scenarios_root}")
            return executable_scenarios

        for scenario_dir in scenarios_root.iterdir():
            if not scenario_dir.is_dir():
                continue

            scenario_name = scenario_dir.name
            scenario_info = GeneralTagHelper.load_single_scenario(
                scenario_dir=scenario_dir,
                scenario_name=scenario_name,
                is_verbose=is_verbose,
            )
            if scenario_info:
                executable_scenarios.append(scenario_info)
                if is_verbose:
                    logger.info(f"可执行 scenario: {scenario_name}")

        logger.info(f"共加载 {len(executable_scenarios)} 个可执行的 scenarios")
        return executable_scenarios

    @staticmethod
    def load_single_scenario(
        scenario_dir: Path,
        scenario_name: str,
        is_verbose: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        加载并验证单个 scenario（合并发现、加载、验证逻辑）

        Returns:
            Optional[Dict[str, Any]]: 可执行的 scenario 信息，如果验证失败返回 None
        """
        # 1. 检查 tag_worker.py 是否存在（递归查找）
        worker_file_path = FileUtil.find_file_in_folder(
            "tag_worker.py",
            str(scenario_dir),
            is_recursively=True,
        )
        if not worker_file_path:
            if is_verbose:
                logger.warning(f"Scenario '{scenario_name}' 缺少 tag_worker.py 文件")
            return None

        # 2. 检查 settings.py 是否存在（递归查找）
        settings_file_path = FileUtil.find_file_in_folder(
            "settings.py",
            str(scenario_dir),
            is_recursively=True,
        )
        if not settings_file_path:
            if is_verbose:
                logger.warning(f"Scenario '{scenario_name}' 缺少 settings.py 文件")
            return None

        # 3. 加载 settings 文件
        try:
            settings = SettingsManager.load_settings_from_file(settings_file_path)
        except Exception as e:
            logger.warning(
                f"加载 scenario '{scenario_name}' 的 settings 失败: {e}",
                exc_info=True,
            )
            return None

        # 4. 加载 worker 类
        try:
            worker_class = GeneralTagHelper._load_worker(Path(worker_file_path))
        except Exception as e:
            logger.warning(
                f"加载 scenario '{scenario_name}' 的 worker 失败: {e}",
                exc_info=True,
            )
            return None

        # 5. 检查 is_enabled 字段
        if "is_enabled" not in settings:
            logger.warning(f"Scenario '{scenario_name}' 缺少 'is_enabled' 字段，跳过")
            return None

        if not settings.get("is_enabled", False):
            if is_verbose:
                logger.info(f"Scenario '{scenario_name}' 被禁用 (is_enabled=False)，跳过")
            return None

        # 6. 验证 settings（结构和枚举）
        try:
            SettingsManager.validate_settings(settings)
        except ValueError as e:
            logger.warning(
                f"Scenario '{scenario_name}' 的 settings 验证失败: {e}，跳过"
            )
            return None

        # 7. 返回可执行的 scenario 信息
        return {
            "scenario_name": scenario_name,
            "worker_class": worker_class,
            "settings": settings,
            "worker_file_path": worker_file_path,
            "settings_file_path": settings_file_path,
        }

    @staticmethod
    def _load_worker(worker_file: Path) -> type[BaseTagWorker]:
        """
        加载 worker 类（从 tag_worker.py 文件）
        """
        spec = importlib.util.spec_from_file_location("tag_worker", worker_file)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 worker 文件: {worker_file}")

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise ValueError(f"Worker 文件语法错误: {worker_file}\n{str(e)}")
        except Exception as e:
            raise ValueError(f"导入 worker 文件失败: {worker_file}\n{str(e)}")

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
            raise ValueError(
                f"Worker 文件中没有找到继承自 BaseTagWorker 的类: {worker_file}"
            )

        return worker_class