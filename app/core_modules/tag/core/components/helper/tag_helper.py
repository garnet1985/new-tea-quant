from typing import Dict, Optional, Type
from pathlib import Path
import importlib.util
import logging

from app.tag.core.base_tag_worker import BaseTagWorker
from app.tag.core.enums import FileName
from utils.file.file_util import FileUtil

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
        加载 scenario 目录中的 settings.py 文件（简单粗暴，不做验证）
        
        Args:
            scenario_dir: Scenario 目录路径
            
        Returns:
            Tuple[Optional[Path], Optional[Dict[str, Any]]]: 
            - (settings_path, settings_dict) 如果成功
            - (None, None) 如果失败（找不到文件或没有 Settings 变量）
        """
        # 1. 查找 settings.py 文件
        settings_file_path = FileUtil.find_file_in_folder(
            FileName.SETTINGS.value,
            str(scenario_dir),
            is_recursively=True,
        )
        
        if not settings_file_path:
            return None, None
        
        settings_path = Path(settings_file_path)
        
        # 2. 读取 settings 变量（不做验证）
        try:
            spec = importlib.util.spec_from_file_location("tag_settings", str(settings_path))
            if spec is None or spec.loader is None:
                return None, None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 提取 Settings 变量
            if not hasattr(module, "Settings"):
                return None, None
            
            settings_dict = module.Settings
            if not isinstance(settings_dict, dict):
                return None, None
            
            return settings_path, settings_dict
        except Exception:
            # 任何错误都返回 None
            return None, None

    @staticmethod
    def load_worker_class(scenario_folder: Path) -> tuple[Optional[Path], Optional[Type[BaseTagWorker]]]:
        """
        加载 scenario 的 worker_class（简单粗暴，不做验证）
        
        Args:
            scenario_folder: Scenario 目录路径
        
        Returns:
            Tuple[Optional[Path], Optional[Type[BaseTagWorker]]]:
            - (worker_file_path, worker_class) 如果成功
            - (None, None) 如果失败（找不到文件或没有继承 BaseTagWorker 的类）
        """
        # 1. 查找 tag_worker.py 文件
        tag_worker_file_path = FileUtil.find_file_in_folder(
            FileName.TAG_WORKER.value,
            str(scenario_folder),
            is_recursively=True,
        )
        
        if not tag_worker_file_path:
            return None, None
        
        worker_file_path = Path(tag_worker_file_path)
        
        # 2. 读取 worker_class（不做验证，只检查是否继承 BaseTagWorker）
        try:
            spec = importlib.util.spec_from_file_location("tag_worker", worker_file_path)
            if spec is None or spec.loader is None:
                return None, None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找继承自 BaseTagWorker 的类
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
                return None, None
            
            return worker_file_path, worker_class
        except Exception:
            # 任何错误都返回 None
            return None, None
