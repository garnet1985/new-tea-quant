"""
数据库配置 - 兼容层

实际配置已迁移到 config/database/db_config.json
此文件仅作为向后兼容的导入层
"""
import os
import json

def load_db_config():
    """加载数据库配置"""
    # 尝试从 JSON 文件加载
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'config', 'database', 'db_config.json'
    )
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 如果 JSON 不存在，使用环境变量
    return {
        'base': {
            'name': 'stocks-py',
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'stocks-py'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'charset': 'utf8mb4',
            'autocommit': True,
        },
        'pool': {
            'pool_size_min': 5,
            'pool_size_max': 30
        },
        'performance': {
            'max_allowed_packet': 1073741824,
        },
        'timeout': {
            'connection': 60,
            'read': 60,
            'write': 60,
        },
        'thread_safety': {
            'enable': True,
            'queue_size': 1000,
            'turn_to_batch_threshold': 1000,
            'max_retries': 3,
        },
        'stock_list': {
            'ts_code_exclude_list': ['688%', '%BJ%']
        }
    }

DB_CONFIG = load_db_config()

__all__ = ['DB_CONFIG']
