"""
数据库配置加载模块

支持统一的数据库配置，可以配置 PostgreSQL、MySQL 或 SQLite。
从 config/database/db_conf.json 加载配置（如果存在），否则从 config/database/db_config.json 加载。
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
    # app/core/conf/db_conf.py -> 项目根
    project_root = current_file.parent.parent.parent.parent
    
    # 优先尝试 db_conf.json（旧格式）
    conf_path = project_root / "config" / "database" / "db_conf.json"
    
    # 如果不存在，尝试 db_config.json（新格式）
    if not conf_path.exists():
        conf_path = project_root / "config" / "database" / "db_config.json"
    
    if not conf_path.exists():
        raise FileNotFoundError(
            f"数据库配置文件不存在: {conf_path}\n"
            f"请确保已创建 config/database/db_conf.json 或 config/database/db_config.json"
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
