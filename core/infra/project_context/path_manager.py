"""
Path Manager - 路径管理器

职责：提供常用路径的快捷访问，所有路径基于项目根目录。

设计原则：
- 所有路径都基于项目根目录（通过 __file__ 自动检测）
- 提供静态方法，无状态
- 支持路径不存在时的处理（返回 Path 对象，不强制创建）
"""

from pathlib import Path
from typing import Optional


class PathManager:
    """路径管理器 - 提供常用路径的快捷访问"""
    
    _root_cache: Optional[Path] = None
    
    @staticmethod
    def get_root() -> Path:
        """
        获取项目根目录
        
        检测逻辑：
        1. 从当前文件（__file__）向上查找，直到找到包含特定标记的目录
        2. 标记可以是：.git、pyproject.toml、setup.py、README.md 等
        3. 缓存结果，避免重复检测
        
        Returns:
            项目根目录的 Path 对象
        """
        if PathManager._root_cache is not None:
            return PathManager._root_cache
        
        # 从当前文件向上查找项目根目录
        current_file = Path(__file__).resolve()
        current_dir = current_file.parent
        
        # 项目根目录的标记文件/目录
        root_markers = [
            '.git',
            'README.md',
            'pyproject.toml',
            'setup.py',
            'requirements.txt',
            'start.py',  # 项目入口文件
        ]
        
        # 向上查找，直到找到包含标记的目录
        for parent in [current_dir] + list(current_dir.parents):
            # 检查是否有标记文件/目录
            for marker in root_markers:
                marker_path = parent / marker
                if marker_path.exists():
                    PathManager._root_cache = parent
                    return parent
        
        # 如果没找到，使用当前文件的第5层父目录（app/core/infra/path -> 项目根）
        # 这是fallback方案
        fallback_root = current_dir.parent.parent.parent.parent.parent
        PathManager._root_cache = fallback_root
        return fallback_root
    
    @staticmethod
    def core() -> Path:
        """
        core/ 目录
        
        支持两种路径结构：
        1. core/（新结构）
        2. app/core/（旧结构，迁移期间兼容）
        """
        root = PathManager.get_root()
        
        # 优先使用新路径结构
        new_path = root / "core"
        if new_path.exists():
            return new_path
        
        # 兼容旧路径结构
        old_path = root / "app" / "core"
        if old_path.exists():
            return old_path
        
        # 如果都不存在，返回新路径（由调用方决定是否创建）
        return new_path
    
    @staticmethod
    def userspace() -> Path:
        """
        userspace/ 目录
        
        支持两种路径结构：
        1. userspace/（新结构）
        2. app/userspace/（旧结构，迁移期间兼容）
        """
        root = PathManager.get_root()
        
        # 优先使用新路径结构
        new_path = root / "userspace"
        if new_path.exists():
            return new_path
        
        # 兼容旧路径结构
        old_path = root / "app" / "userspace"
        if old_path.exists():
            return old_path
        
        # 如果都不存在，返回新路径（由调用方决定是否创建）
        return new_path
    
    @staticmethod
    def config() -> Path:
        """
        config/ 目录（用户配置文件）
        
        支持两种路径结构：
        1. core/config/（新结构）
        2. config/（旧结构，迁移期间兼容）
        """
        root = PathManager.get_root()
        
        # 优先使用新路径结构
        new_path = root / "core" / "config"
        if new_path.exists():
            return new_path
        
        # 兼容旧路径结构
        old_path = root / "config"
        if old_path.exists():
            return old_path
        
        # 如果都不存在，返回新路径（由调用方决定是否创建）
        return new_path
    
    @staticmethod
    def strategy(strategy_name: str) -> Path:
        """策略目录：userspace/strategies/{strategy_name}"""
        return PathManager.userspace() / "strategies" / strategy_name
    
    @staticmethod
    def strategy_settings(strategy_name: str) -> Path:
        """策略配置文件：userspace/strategies/{strategy_name}/settings.py"""
        return PathManager.strategy(strategy_name) / "settings.py"
    
    @staticmethod
    def strategy_results(strategy_name: str) -> Path:
        """策略结果目录：userspace/strategies/{strategy_name}/results"""
        return PathManager.strategy(strategy_name) / "results"
    
    @staticmethod
    def tag_scenario(scenario_name: str) -> Path:
        """标签场景目录：userspace/tags/{scenario_name}"""
        return PathManager.userspace() / "tags" / scenario_name
    
    # ========== Data Source 相关路径 ==========
    
    @staticmethod
    def data_source() -> Path:
        """Data Source 根目录：userspace/data_source"""
        return PathManager.userspace() / "data_source"
    
    @staticmethod
    def data_source_mapping() -> Path:
        """Data Source 用户配置文件：userspace/data_source/mapping.json"""
        return PathManager.data_source() / "mapping.json"
    
    @staticmethod
    def data_source_handlers() -> Path:
        """Data Source Handlers 目录：userspace/data_source/handlers"""
        return PathManager.data_source() / "handlers"
    
    @staticmethod
    def data_source_handler(handler_name: str) -> Path:
        """Data Source Handler 目录：userspace/data_source/handlers/{handler_name}"""
        return PathManager.data_source_handlers() / handler_name
    
    @staticmethod
    def data_source_providers() -> Path:
        """Data Source Providers 目录：userspace/data_source/providers"""
        return PathManager.data_source() / "providers"
    
    @staticmethod
    def data_source_provider(provider_name: str) -> Path:
        """Data Source Provider 目录：userspace/data_source/providers/{provider_name}"""
        return PathManager.data_source_providers() / provider_name
