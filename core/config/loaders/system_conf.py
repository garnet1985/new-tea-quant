"""
系统配置加载模块

从 core/config/system.json 加载系统常量配置。
支持 userspace/config/system.json 覆盖（用户全局配置）。
"""
import json
from pathlib import Path
from loguru import logger
from typing import Dict, Any


def load_system_conf() -> Dict[str, Any]:
    """
    加载系统配置文件
    
    Returns:
        dict: 系统配置字典
    """
    # 从当前文件位置向上找到项目根目录
    current_file = Path(__file__).resolve()
    # core/config/loaders/system_conf.py -> 项目根（4层向上：loaders -> config -> core -> 项目根）
    project_root = current_file.parent.parent.parent.parent
    
    # 配置加载优先级：
    # 1. userspace/config/system.json (用户全局配置，最高优先级)
    # 2. core/config/system.json (系统默认配置)
    
    user_config_path = project_root / "userspace" / "config" / "system.json"
    default_config_path = project_root / "core" / "config" / "system.json"
    
    # 按优先级查找配置文件
    config_path = None
    if user_config_path.exists():
        config_path = user_config_path
    elif default_config_path.exists():
        config_path = default_config_path
    
    if config_path is None:
        raise FileNotFoundError(
            f"系统配置文件不存在\n"
            f"请创建以下任一配置文件：\n"
            f"  - userspace/config/system.json (用户全局配置，推荐)\n"
            f"  - core/config/system.json (系统默认配置)"
        )
    
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        
        return config
        
    except json.JSONDecodeError as e:
        raise ValueError(f"系统配置文件格式错误: {e}")
    except Exception as e:
        logger.error(f"加载系统配置失败: {e}")
        raise


# 全局配置对象
SYSTEM_CONF = load_system_conf()

# 导出常用常量（向后兼容）
data_default_start_date = SYSTEM_CONF.get('data_default_start_date', '20080101')
kline_terms = SYSTEM_CONF.get('kline_terms', ['daily', 'weekly', 'monthly'])
default_decimal_places = SYSTEM_CONF.get('default_decimal_places', 2)
stock_index_indicators = SYSTEM_CONF.get('stock_index_indicators', {})

__all__ = [
    'SYSTEM_CONF',
    'load_system_conf',
    'data_default_start_date',
    'kline_terms',
    'default_decimal_places',
    'stock_index_indicators'
]
