"""
数据库配置加载模块

支持统一的数据库配置，可以配置 PostgreSQL、MySQL 或 SQLite。
从 core/config/database/db_conf.json 加载配置（如果存在），否则从 core/config/database/db_config.json 加载。
支持 userspace/config/database/ 覆盖（用户全局配置）。
支持旧路径结构 config/database/（向后兼容）。
"""
import json
from pathlib import Path
from loguru import logger
from typing import Dict, Any, Optional


def load_db_conf() -> Dict[str, Any]:
    """
    加载数据库配置文件
    
    配置格式（统一配置）：
       {
         "database_type": "postgresql" | "mysql" | "sqlite",
         "postgresql": {...},
         "mysql": {...},
         "sqlite": {...},
         "batch_write": {...}
       }
    
    Returns:
        dict: 数据库配置字典
    """
    # 从当前文件位置向上找到项目根目录
    current_file = Path(__file__).resolve()
    # core/config/loaders/db_conf.py -> 项目根（4层向上：loaders -> config -> core -> 项目根）
    # 旧路径：core/conf/db_conf.py -> 项目根（3层向上：conf -> core -> 项目根）
    project_root = current_file.parent.parent.parent.parent
    
    # 配置加载优先级：
    # 1. userspace/config/database/ (用户全局配置，最高优先级)
    # 2. core/config/database/ (系统默认配置)
    # 3. config/database/ (旧路径，向后兼容)
    
    # 优先尝试用户全局配置
    user_conf_path = project_root / "userspace" / "config" / "database" / "db_conf.json"
    user_config_path = project_root / "userspace" / "config" / "database" / "db_config.json"
    
    # 系统默认配置路径
    default_conf_path = project_root / "core" / "config" / "database" / "db_conf.json"
    default_config_path = project_root / "core" / "config" / "database" / "db_config.json"
    
    # 旧路径（向后兼容）
    legacy_conf_path = project_root / "config" / "database" / "db_conf.json"
    legacy_config_path = project_root / "config" / "database" / "db_config.json"
    
    # 按优先级查找配置文件
    conf_path = None
    if user_conf_path.exists():
        conf_path = user_conf_path
    elif user_config_path.exists():
        conf_path = user_config_path
    elif default_conf_path.exists():
        conf_path = default_conf_path
    elif default_config_path.exists():
        conf_path = default_config_path
    elif legacy_conf_path.exists():
        conf_path = legacy_conf_path
    elif legacy_config_path.exists():
        conf_path = legacy_config_path
    
    if conf_path is None:
        raise FileNotFoundError(
            f"数据库配置文件不存在\n"
            f"请创建以下任一配置文件：\n"
            f"  - userspace/config/database/db_config.json (用户全局配置，推荐)\n"
            f"  - core/config/database/db_config.json (系统默认配置)\n"
            f"  - config/database/db_config.json (旧路径，向后兼容)"
        )
    
    try:
        with conf_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 检查是否是新格式（有 database_type）
        if 'database_type' in config:
            # 新格式：统一配置
            database_type = config.get('database_type', 'postgresql').lower()
            
            # 验证对应数据库的配置存在
            if database_type == 'postgresql':
                if 'postgresql' not in config:
                    raise ValueError("PostgreSQL 配置缺失，请提供 'postgresql' 配置项")
            elif database_type == 'mysql':
                if 'mysql' not in config:
                    raise ValueError("MySQL 配置缺失，请提供 'mysql' 配置项")
            elif database_type == 'sqlite':
                if 'sqlite' not in config:
                    raise ValueError("SQLite 配置缺失，请提供 'sqlite' 配置项")
            else:
                raise ValueError(f"不支持的数据库类型: {database_type}，支持的类型: 'postgresql', 'mysql', 'sqlite'")
            
            # 确保 batch_write 配置存在
            if 'batch_write' not in config:
                config['batch_write'] = {
                    'batch_size': 1000,
                    'flush_interval': 5.0,
                    'enable': True
                }
            
            return config
        
        # 旧格式：自动检测（向后兼容）
        elif 'db_path' in config:
            logger.info("🔍 检测到旧格式配置（db_path），自动转换为 SQLite 配置")
            
            # 转换为新格式（SQLite）
            new_config = {
                'database_type': 'sqlite',
                'sqlite': {
                    'db_path': config['db_path'],
                    'timeout': config.get('timeout', 5.0)
                },
                'batch_write': config.get('batch_write', {
                    'batch_size': 1000,
                    'flush_interval': 5.0,
                    'enable': True
                })
            }
            
            return new_config
        
        elif 'host' in config and 'database' in config:
            # 根据端口判断是 MySQL 还是 PostgreSQL
            port = config.get('port', 3306)
            database_type = 'mysql' if port != 5432 else 'postgresql'
            
            logger.info(f"🔍 检测到旧格式配置（host+database），自动转换为 {database_type} 配置")
            
            new_config = {
                'database_type': database_type,
                database_type: config,
                'batch_write': config.get('batch_write', {
                    'batch_size': 1000,
                    'flush_interval': 5.0,
                    'enable': True
                })
            }
            
            return new_config
        
        else:
            raise ValueError("配置文件格式错误：必须包含 'database_type' 或 'db_path' 或 'host'+'database'")
            
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件格式错误: {e}")
    except Exception as e:
        logger.error(f"加载数据库配置失败: {e}")
        raise


# 全局配置对象
DB_CONF = load_db_conf()

__all__ = ['DB_CONF', 'load_db_conf']
