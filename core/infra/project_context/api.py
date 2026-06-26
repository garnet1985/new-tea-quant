"""
Project Context API - 对外接口定义

职责：定义所有对外API的抽象接口，确保契约稳定

设计原则：
- 单一入口点：用户只通过 ProjectContextManager 访问功能
- API契约明确：抽象类定义所有对外API
- 防止误用：内部Manager不对外暴露
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List


class ProjectContextAPI(ABC):
    """
    Project Context API - 对外接口定义
    
    所有对外API在此定义，确保契约稳定。
    用户只能通过 ProjectContextManager 访问功能。
    """
    
    # ========== 路径核心 API（5个）==========
    
    @abstractmethod
    def get_project_root(self) -> Path:
        """获取项目根目录"""
        pass
    
    @abstractmethod
    def get_core_root(self) -> Path:
        """获取 core 目录"""
        pass
    
    @abstractmethod
    def get_userspace_root(self) -> Path:
        """获取 userspace 目录"""
        pass
    
    @abstractmethod
    def get_strategy_directory(self, strategy_name: str) -> Path:
        """获取指定策略的目录"""
        pass
    
    @abstractmethod
    def get_tag_directory(self, tag_name: str) -> Path:
        """获取指定 Tag scenario 的目录"""
        pass
    
    # ========== 配置核心 API（3个）==========
    
    @abstractmethod
    def load_core_config(self, config_name: str) -> Dict[str, Any]:
        """加载 core 配置"""
        pass
    
    @abstractmethod
    def load_database_config(self, database_type: Optional[str] = None) -> Dict[str, Any]:
        """加载数据库配置"""
        pass
    
    @abstractmethod
    def load_data_config(self) -> Dict[str, Any]:
        """加载 data.json 配置"""
        pass
    
    # ========== 发现核心 API（3个）==========
    
    @abstractmethod
    def discover_strategies(self) -> List[str]:
        """发现所有策略"""
        pass
    
    @abstractmethod
    def discover_tags(self) -> List[str]:
        """发现所有 Tag scenario"""
        pass
    
    @abstractmethod
    def discover_configs(self) -> Dict[str, Dict[str, Any]]:
        """发现所有 core 配置"""
        pass
    
    # ========== 文件核心 API（2个）==========
    
    @abstractmethod
    def find_file(self, filename: str, search_dir: Path, recursive: bool = True) -> Optional[Path]:
        """查找单个文件"""
        pass
    
    @abstractmethod
    def load_file_content(self, path: Path, encoding: str = "utf-8") -> Optional[str]:
        """加载文件内容"""
        pass
    
    # ========== 元数据核心 API（2个）==========
    
    @abstractmethod
    def core_version(self) -> Optional[str]:
        """获取 core 版本号"""
        pass
    
    @abstractmethod
    def core_info(self) -> Optional[Dict[str, Any]]:
        """获取 core meta 信息"""
        pass
    
    # ========== 缓存管理 API（1个）==========
    
    @abstractmethod
    def clear_userspace_cache(self) -> None:
        """清理 userspace 路径缓存"""
        pass