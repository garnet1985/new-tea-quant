"""
Worker 配置加载模块

从 core/config/worker.json 加载 Worker 配置。
支持 userspace/config/worker.json 覆盖（用户全局配置）。
"""
import json
from pathlib import Path
from loguru import logger
from typing import Dict, Any
from enum import Enum


def load_worker_conf() -> Dict[str, Any]:
    """
    加载 Worker 配置文件
    
    Returns:
        dict: Worker 配置字典
    """
    # 从当前文件位置向上找到项目根目录
    current_file = Path(__file__).resolve()
    # core/config/loaders/worker_conf.py -> 项目根（4层向上：loaders -> config -> core -> 项目根）
    project_root = current_file.parent.parent.parent.parent
    
    # 配置加载优先级：
    # 1. userspace/config/worker.json (用户全局配置，最高优先级)
    # 2. core/config/worker.json (系统默认配置)
    
    user_config_path = project_root / "userspace" / "config" / "worker.json"
    default_config_path = project_root / "core" / "config" / "worker.json"
    
    # 按优先级查找配置文件
    config_path = None
    if user_config_path.exists():
        config_path = user_config_path
    elif default_config_path.exists():
        config_path = default_config_path
    
    if config_path is None:
        raise FileNotFoundError(
            f"Worker 配置文件不存在\n"
            f"请创建以下任一配置文件：\n"
            f"  - userspace/config/worker.json (用户全局配置，推荐)\n"
            f"  - core/config/worker.json (系统默认配置)"
        )
    
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        
        return config
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Worker 配置文件格式错误: {e}")
    except Exception as e:
        logger.error(f"加载 Worker 配置失败: {e}")
        raise


def _string_to_task_type(task_type_str: str):
    """将字符串转换为 TaskType 枚举（延迟导入避免循环依赖）"""
    # 延迟导入避免循环依赖
    from core.infra.worker.multi_process.task_type import TaskType
    
    task_type_map = {
        'CPU_INTENSIVE': TaskType.CPU_INTENSIVE,
        'IO_INTENSIVE': TaskType.IO_INTENSIVE,
        'MIXED': TaskType.MIXED,
    }
    return task_type_map.get(task_type_str.upper(), TaskType.MIXED)


def get_module_config(module_name: str) -> dict:
    """
    获取模块的任务配置
    
    Args:
        module_name: 模块名称
    
    Returns:
        配置字典 {'task_type': TaskType, 'reserve_cores': int}
    """
    worker_conf = load_worker_conf()
    
    module_task_config = worker_conf.get('module_task_config', {})
    default_task_config = worker_conf.get('default_task_config', {
        'task_type': 'MIXED',
        'reserve_cores': 2
    })
    
    # 获取模块配置或使用默认配置
    module_config = module_task_config.get(module_name, default_task_config)
    
    # 转换 task_type 字符串为枚举
    task_type_str = module_config.get('task_type', 'MIXED')
    task_type = _string_to_task_type(task_type_str)
    
    return {
        'task_type': task_type,
        'reserve_cores': module_config.get('reserve_cores', 2)
    }


# 全局配置对象
WORKER_CONF = load_worker_conf()

# 导出 MODULE_TASK_CONFIG 和 DEFAULT_TASK_CONFIG（向后兼容，但已转换为枚举）
# 注意：这些是动态生成的，不是静态字典
__all__ = [
    'WORKER_CONF',
    'load_worker_conf',
    'get_module_config'
]
