"""
数据库配置加载器

从 config/database/db_config.json 加载配置
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
    
    # 如果 JSON 不存在，返回空配置（DuckDB 使用独立配置）
    return {}

DB_CONFIG = load_db_config()

__all__ = ['DB_CONFIG']
