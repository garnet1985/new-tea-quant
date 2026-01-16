"""
Tushare Provider 配置

从独立配置文件加载认证信息和其他配置
"""
import os
from pathlib import Path
from loguru import logger


def get_config() -> dict:
    """
    获取 Tushare Provider 配置
    
    配置来源：
    1. auth_token.txt 文件（用户上传，gitignore）
    2. 环境变量 TUSHARE_TOKEN
    3. 默认配置
    
    Returns:
        配置字典
    """
    config = {}
    
    # 1. 优先从 auth_token.txt 读取（用户上传的文件）
    # 使用 PathManager 获取正确的路径
    from core.infra.project_context import PathManager
    auth_token_path = PathManager.data_source_provider("tushare") / "auth_token.txt"
    if auth_token_path.exists():
        try:
            # 读取文件内容，去除首尾空白字符
            token = auth_token_path.read_text(encoding='utf-8').strip()
            if token:
                config['token'] = token
            else:
                logger.warning("auth_token.txt exists but is empty")
        except Exception as e:
            logger.warning(f"Failed to load auth_token.txt: {e}")
    
    # 2. 如果没有，尝试从环境变量读取
    if 'token' not in config:
        token = os.getenv('TUSHARE_TOKEN')
        if token:
            config['token'] = token
    
    # 3. 如果还没有，报错
    if 'token' not in config:
        from core.infra.project_context import PathManager
        provider_path = PathManager.data_source_provider("tushare")
        raise ValueError(
            "Tushare token not found. Please:\n"
            f"  1. Create {provider_path}/auth_token.txt with your token (one line)\n"
            "  2. Or set environment variable: TUSHARE_TOKEN=your_token"
        )
    
    return config
