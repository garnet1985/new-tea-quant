"""
数据库配置加载器

⚠️ DEPRECATED: 本模块已废弃，请使用 core.infra.project_context.ConfigManager.get_database_config() 替代

从 config/database/db_config.json 加载配置
"""
import os
import json

def load_db_config():
    """加载数据库配置"""
    # 尝试从 JSON 文件加载
    # 从 core/infra/db 向上找到项目根，再定位到 core/config/database/
    # 支持新旧路径结构
    current_dir = os.path.dirname(__file__)  # core/infra/db
    project_root = os.path.dirname(os.path.dirname(current_dir))  # 项目根（从 core/infra/db 向上2层）
    
    # 优先尝试新路径结构
    config_path = os.path.join(project_root, 'core', 'config', 'database', 'db_config.json')
    
    # 如果不存在，尝试旧路径结构
    if not os.path.exists(config_path):
        config_path = os.path.join(project_root, 'config', 'database', 'db_config.json')
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 如果 JSON 不存在，返回空配置（DuckDB 使用独立配置）
    return {}

DB_CONFIG = load_db_config()

__all__ = ['DB_CONFIG']
