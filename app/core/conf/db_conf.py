"""
DuckDB 配置加载模块

从 config/database/db_conf.json 加载 DuckDB 配置
"""
import json
from pathlib import Path
from loguru import logger


def load_duckdb_conf():
    """
    加载 DuckDB 配置文件
    
    Returns:
        dict: DuckDB 配置字典，包含 db_path, threads, memory_limit
    """
    # 从当前文件位置向上找到项目根目录
    current_file = Path(__file__).resolve()
    # app/core/conf/db_conf.py -> 项目根
    project_root = current_file.parent.parent.parent.parent
    
    conf_path = project_root / "config" / "database" / "db_conf.json"
    
    if not conf_path.exists():
        raise FileNotFoundError(
            f"DuckDB 配置文件不存在: {conf_path}\n"
            f"请确保已创建 config/database/db_conf.json"
        )
    
    try:
        with conf_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 验证必需字段
        required_fields = ["db_path"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"DuckDB 配置缺少必需字段: {field}")
        
        # 确保 batch_write 配置存在（使用默认值）
        if 'batch_write' not in config:
            config['batch_write'] = {
                'batch_size': 1000,
                'flush_interval': 5.0,
                'enable': True
            }
        
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"DuckDB 配置文件格式错误: {e}")
    except Exception as e:
        logger.error(f"加载 DuckDB 配置失败: {e}")
        raise


# 全局配置对象
DUCKDB_CONF = load_duckdb_conf()

__all__ = ['DUCKDB_CONF', 'load_duckdb_conf']
