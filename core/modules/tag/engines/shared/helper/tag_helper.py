from typing import Any, Dict, Optional, Type
from pathlib import Path
import importlib.util
import logging
import sys

from core.modules.tag.engines.shared.base_worker import BaseTagWorker
from core.modules.tag.enums import FileName
from core.infra.discovery import FileUtils

logger = logging.getLogger(__name__)


class TagHelper:
    """
    Tag Helper - Tag 系统辅助函数

    职责：
    1. 加载 scenario settings 文件
    2. 加载 worker class 文件
    """

    @staticmethod
    def load_scenario_settings(scenario_dir: Path) -> tuple[Optional[Path], Optional[Dict[str, Any]]]:
        """
        加载 scenario 目录中的 settings.py 文件
        
        Args:
            scenario_dir: Scenario 目录路径
            
        Returns:
            Tuple[Optional[Path], Optional[Dict[str, Any]]]: 
            - (settings_path, settings_dict) 如果成功
            - (None, None) 如果失败（找不到文件或没有 Settings 变量）
        """
        # 1. 查找 settings.py 文件
        settings_path = FileUtils.find_file(
            scenario_dir if isinstance(scenario_dir, Path) else Path(scenario_dir),
            FileName.SETTINGS.value
        )
        
        if not settings_path:
            return None, None

        # 2. 使用 FileUtils 加载 settings 变量
        settings_dict = FileUtils.load_python_config(settings_path, var_name="Settings")
        
        if not settings_dict or not isinstance(settings_dict, dict):
            return None, None
        
        return settings_path, settings_dict

    @staticmethod
    def load_worker_class(scenario_folder: Path) -> tuple[Optional[Path], Optional[Type[BaseTagWorker]]]:
        """
        加载 scenario 的 worker_class
        
        Args:
            scenario_folder: Scenario 目录路径
        
        Returns:
            Tuple[Optional[Path], Optional[Type[BaseTagWorker]]]:
            - (worker_file_path, worker_class) 如果成功
            - (None, None) 如果失败（找不到文件或没有继承 BaseTagWorker 的类）
        """
        # 1. 查找 tag_worker.py 文件
        worker_file_path = FileUtils.find_file(
            scenario_folder if isinstance(scenario_folder, Path) else Path(scenario_folder),
            FileName.TAG_WORKER.value
        )
        
        if not worker_file_path:
            return None, None
        
        # 2. 加载模块并查找继承自 BaseTagWorker 的类
        try:
            module_name = f"tag_worker_{scenario_folder.name}"
            spec = importlib.util.spec_from_file_location(module_name, worker_file_path)
            if spec is None or spec.loader is None:
                return None, None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找继承自 BaseTagWorker 的类（排除基类本身）
            for name, obj in module.__dict__.items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseTagWorker)
                    and obj is not BaseTagWorker
                ):
                    return worker_file_path, obj
            
            return None, None
        except Exception as e:
            logger.debug(f"加载 worker class 失败 {worker_file_path}: {e}")
            return None, None
