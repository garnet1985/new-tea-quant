#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


class ConfigManager:
    """
    配置管理器
    统一管理应用程序的所有配置项
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 默认配置
        self.default_config = {
            'database': {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'database': 'stocks-py',
                'charset': 'utf8mb4',
                'autocommit': True,
                'pool_size_min': 5,
                'pool_size_max': 30,
                'max_allowed_packet': 16777216 * 64,
                'connection_timeout': 60,
                'read_timeout': 60,
                'write_timeout': 60
            },
            'tushare': {
                'token_file': 'app/data_source/providers/tushare/auth/token.txt',
                'base_url': 'http://api.tushare.pro',
                'timeout': 30,
                'retry_times': 3,
                'retry_delay': 1
            },
            'performance': {
                'max_workers': 5,
                'batch_size': 100,
                'flush_interval': 5,
                'max_history': 1000,
                'monitor_enabled': True
            },
            'logging': {
                'level': 'INFO',
                'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}',
                'file': 'logs/app.log',
                'max_size': '10MB',
                'rotation': '1 day',
                'retention': '30 days'
            },
            'storage': {
                'data_dir': 'data',
                'cache_dir': 'data/cache',
                'backup_enabled': True,
                'backup_interval': 3600
            }
        }
        
        # 加载配置
        self.config = self.load_config()
        
        logger.info("配置管理器已初始化")
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            dict: 配置字典
        """
        config_file = self.config_dir / "app_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                logger.info(f"从 {config_file} 加载配置")
                return self.merge_config(self.default_config, loaded_config)
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        else:
            logger.info("配置文件不存在，创建默认配置文件")
            self.save_config(self.default_config)
        
        return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        保存配置到文件
        
        Args:
            config: 配置字典
        """
        config_file = self.config_dir / "app_config.json"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到 {config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def merge_config(self, default: Dict[str, Any], custom: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并默认配置和自定义配置
        
        Args:
            default: 默认配置
            custom: 自定义配置
            
        Returns:
            dict: 合并后的配置
        """
        result = default.copy()
        
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        # 导航到父级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """
        批量更新配置
        
        Args:
            updates: 要更新的配置字典
        """
        for key, value in updates.items():
            self.set(key, value)
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        获取数据库配置
        
        Returns:
            dict: 数据库配置
        """
        return self.get('database', {})
    
    def get_tushare_config(self) -> Dict[str, Any]:
        """
        获取Tushare配置
        
        Returns:
            dict: Tushare配置
        """
        return self.get('tushare', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """
        获取性能配置
        
        Returns:
            dict: 性能配置
        """
        return self.get('performance', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        获取日志配置
        
        Returns:
            dict: 日志配置
        """
        return self.get('logging', {})
    
    def reload(self) -> None:
        """重新加载配置"""
        self.config = self.load_config()
        logger.info("配置已重新加载")
    
    def export_env_vars(self) -> None:
        """
        将配置导出为环境变量
        主要用于兼容现有的环境变量配置方式
        """
        db_config = self.get_database_config()
        
        # 数据库配置
        os.environ.setdefault('DB_HOST', str(db_config.get('host', 'localhost')))
        os.environ.setdefault('DB_PORT', str(db_config.get('port', 3306)))
        os.environ.setdefault('DB_USER', str(db_config.get('user', 'root')))
        os.environ.setdefault('DB_PASSWORD', str(db_config.get('password', '')))
        os.environ.setdefault('DB_NAME', str(db_config.get('database', 'stocks-py')))
        
        logger.info("配置已导出为环境变量")


# 全局配置管理器实例
_global_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值的便捷函数
    
    Args:
        key: 配置键
        default: 默认值
        
    Returns:
        Any: 配置值
    """
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any) -> None:
    """
    设置配置值的便捷函数
    
    Args:
        key: 配置键
        value: 配置值
    """
    get_config_manager().set(key, value) 