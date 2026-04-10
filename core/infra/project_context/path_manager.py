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
import os


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
        
        优先级：
        1. 环境变量覆盖：
           - NEW_TEA_QUANT_USERSPACE_ROOT
           - 或 NTQ_USERSPACE_ROOT（别名）
        2. 相对项目根目录：
           - userspace/（新结构）
           - app/userspace/（旧结构，迁移期间兼容）
        """
        root = PathManager.get_root()
        
        # 1. 环境变量覆盖（允许用户将 userspace 放在项目根目录之外）
        env_paths = [
            os.getenv("NEW_TEA_QUANT_USERSPACE_ROOT"),
            os.getenv("NTQ_USERSPACE_ROOT"),
        ]
        for env_path in env_paths:
            if env_path:
                p = Path(env_path).expanduser().resolve()
                if p.exists():
                    return p
        
        # 2. 优先使用新路径结构（相对项目根目录）
        new_path = root / "userspace"
        if new_path.exists():
            return new_path

        # 如果不存在，返回新路径（由调用方决定是否创建）
        return new_path
    
    @staticmethod
    def default_config() -> Path:
        """默认配置目录：core/default_config/"""
        root = PathManager.get_root()
        return root / "core" / "default_config"

    @staticmethod
    def user_config() -> Path:
        """用户配置目录：userspace/config/"""
        return PathManager.userspace() / "config"

    @staticmethod
    def config() -> Path:
        """用户配置目录（同 `user_config()`，供简短调用）。"""
        return PathManager.user_config()
    
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
    def strategy_opportunity_enums(strategy_name: str, use_sampling: bool = False) -> Path:
        """
        枚举器结果目录
        
        Args:
            strategy_name: 策略名称
            use_sampling: 是否使用采样模式
                - True: test/ 子目录（采样枚举）
                - False: output/ 子目录（完整输出）
        
        Returns:
            userspace/strategies/{strategy_name}/results/opportunity_enums/{test|output}
        """
        sub_dir = "test" if use_sampling else "output"
        return PathManager.strategy_results(strategy_name) / "opportunity_enums" / sub_dir
    
    @staticmethod
    def strategy_simulations_price_factor(strategy_name: str) -> Path:
        """价格因子模拟器结果目录：userspace/strategies/{strategy_name}/results/simulations/price_factor"""
        return PathManager.strategy_results(strategy_name) / "simulations" / "price_factor"
    
    @staticmethod
    def strategy_capital_allocation(strategy_name: str) -> Path:
        """资金分配模拟器结果目录：userspace/strategies/{strategy_name}/results/simulations/capital_allocation"""
        return PathManager.strategy_results(strategy_name) / "simulations" / "capital_allocation"

    @staticmethod
    def strategy_simulations_enumerator(strategy_name: str) -> Path:
        """
        枚举器回测（simulate/simulate_enum）结果目录：
        userspace/strategies/{strategy_name}/results/simulations/enumerator

        注意：这不是 opportunity_enums（枚举输出），而是历史回测 session 结果。
        """
        return PathManager.strategy_results(strategy_name) / "simulations" / "enumerator"
    
    @staticmethod
    def strategy_scan_cache(strategy_name: str) -> Path:
        """扫描缓存目录：userspace/strategies/{strategy_name}/scan_cache"""
        return PathManager.strategy(strategy_name) / "scan_cache"
    
    @staticmethod
    def strategy_scan_results(strategy_name: str) -> Path:
        """扫描结果目录：userspace/strategies/{strategy_name}/results/scan"""
        return PathManager.strategy_results(strategy_name) / "scan"
    
    # ========== Tag 相关路径 ==========
    
    @staticmethod
    def tags() -> Path:
        """Tag 根目录：userspace/tags"""
        return PathManager.userspace() / "tags"
    
    @staticmethod
    def tag_scenario(scenario_name: str) -> Path:
        """标签场景目录：userspace/tags/{scenario_name}"""
        return PathManager.tags() / scenario_name
    
    @staticmethod
    def tag_scenario_settings(scenario_name: str) -> Path:
        """标签场景配置文件：userspace/tags/{scenario_name}/settings.py"""
        return PathManager.tag_scenario(scenario_name) / "settings.py"
    
    @staticmethod
    def tag_scenario_worker(scenario_name: str) -> Path:
        """标签场景 Worker 文件：userspace/tags/{scenario_name}/tag_worker.py"""
        return PathManager.tag_scenario(scenario_name) / "tag_worker.py"
    
    # ========== Data Source 相关路径 ==========
    
    @staticmethod
    def data_source() -> Path:
        """Data Source 根目录：userspace/data_source"""
        return PathManager.userspace() / "data_source"
    
    @staticmethod
    def data_source_mapping() -> Path:
        """Data Source 用户配置文件：userspace/data_source/mapping.py"""
        return PathManager.data_source() / "mapping.py"
    
    @staticmethod
    def data_source_handlers() -> Path:
        """Data Source Handlers 目录：userspace/data_source/handlers"""
        return PathManager.data_source() / "handlers"
    
    @staticmethod
    def data_source_handler(handler_name: str) -> Path:
        """Data Source Handler 目录：userspace/data_source/handlers/{handler_name}"""
        return PathManager.data_source_handlers() / handler_name
    
    @staticmethod
    def find_config_recursively(base_dir: Path, data_source_key: str, config_filename: str = "config.py") -> Optional[Path]:
        """
        递归查找配置文件
        
        Args:
            base_dir: 搜索的根目录
            data_source_key: 数据源键名（用于匹配目录名）
            config_filename: 配置文件名（默认为 "config.py"）
        
        Returns:
            找到的配置文件路径，如果未找到则返回 None
        
        搜索规则：
        1. 首先尝试直接路径：{base_dir}/{data_source_key}/{config_filename}
        2. 如果找不到，递归查找所有包含 {data_source_key} 的目录
        3. 例如：data_source_key="kline_daily" 会匹配 {base_dir}/stock_klines/kline_daily/{config_filename}
        """
        if not base_dir.exists():
            return None
        
        # 首先尝试直接路径（向后兼容）
        direct_path = base_dir / data_source_key / config_filename
        if direct_path.exists() and direct_path.is_file():
            return direct_path
        
        # 递归查找所有包含 data_source_key 的目录
        for path in base_dir.rglob(f"*/{data_source_key}/{config_filename}"):
            if path.exists() and path.is_file():
                return path
        
        # 也支持查找目录名完全匹配的情况
        for path in base_dir.rglob(f"{data_source_key}/{config_filename}"):
            if path.exists() and path.is_file():
                return path
        
        return None
    
    @staticmethod
    def data_contract() -> Path:
        """
        Data Contract 用户注册目录：userspace/data_contract

        与 Python 包 `userspace.data_contract` 对应；路径受 `PathManager.userspace()`
        （含环境变量覆盖）影响，供发现/诊断与文件侧约定一致。
        """
        return PathManager.userspace() / "data_contract"

    @staticmethod
    def data_source_providers() -> Path:
        """Data Source Providers 目录：userspace/data_source/providers"""
        return PathManager.data_source() / "providers"
    
    @staticmethod
    def data_source_provider(provider_name: str) -> Path:
        """Data Source Provider 目录：userspace/data_source/providers/{provider_name}"""
        return PathManager.data_source_providers() / provider_name
