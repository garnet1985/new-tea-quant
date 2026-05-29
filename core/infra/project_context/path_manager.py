"""
Path Manager - 路径管理器

职责：提供常用路径的快捷访问，所有路径基于项目根目录。

userspace 顶层三分：
- strategies/   策略（日常使用）
- extensions/   框架扩展（tags、data_source、data_contract、tables、adapters）
- system/       系统（config、db、backup、updater、.ntq）
"""
from pathlib import Path
from typing import Optional
import os


# userspace/extensions 下 Python 包前缀（import 路径）
EXTENSIONS_MODULE_PREFIX = "userspace.extensions"


def extensions_module(*parts: str) -> str:
    """拼接 extensions 包下模块路径，如 extensions_module('data_source', 'handlers')。"""
    base = EXTENSIONS_MODULE_PREFIX
    return ".".join((base,) + parts) if parts else base


class PathManager:
    """路径管理器 - 提供常用路径的快捷访问"""

    _root_cache: Optional[Path] = None
    _userspace_cache: Optional[Path] = None

    @staticmethod
    def invalidate_userspace_cache() -> None:
        """清理 userspace 路径缓存。用于 setup 运行时路径切换后强制重读。"""
        PathManager._userspace_cache = None

    @staticmethod
    def get_root() -> Path:
        """获取项目根目录。"""
        if PathManager._root_cache is not None:
            return PathManager._root_cache

        current_file = Path(__file__).resolve()
        current_dir = current_file.parent

        root_markers = [
            ".git",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "start.py",
        ]

        for parent in [current_dir] + list(current_dir.parents):
            for marker in root_markers:
                if (parent / marker).exists():
                    PathManager._root_cache = parent
                    return parent

        fallback_root = current_dir.parent.parent.parent.parent.parent
        PathManager._root_cache = fallback_root
        return fallback_root

    @staticmethod
    def core() -> Path:
        """core/ 目录。"""
        root = PathManager.get_root()
        new_path = root / "core"
        if new_path.exists():
            return new_path
        return new_path

    @staticmethod
    def userspace() -> Path:
        """
        userspace/ 目录。

        优先级：环境变量 > .ntq/userspace-path.json > 项目根/userspace
        """
        if PathManager._userspace_cache is not None:
            return PathManager._userspace_cache

        root = PathManager.get_root()

        for env_path in (
            os.getenv("NEW_TEA_QUANT_USERSPACE_ROOT"),
            os.getenv("NTQ_USERSPACE_ROOT"),
        ):
            if env_path:
                p = Path(env_path).expanduser().resolve()
                if p.exists():
                    PathManager._userspace_cache = p
                    return p

        state_file = root / ".ntq" / "userspace-path.json"
        if state_file.is_file():
            try:
                import json

                payload = json.loads(state_file.read_text(encoding="utf-8"))
                state_path = str(payload.get("userspacePath", "")).strip()
                if state_path:
                    p = Path(state_path).expanduser().resolve()
                    if p.exists():
                        PathManager._userspace_cache = p
                        return p
            except Exception:
                pass

        new_path = root / "userspace"
        PathManager._userspace_cache = new_path
        return new_path

    @staticmethod
    def strategies_root() -> Path:
        """策略根目录：userspace/strategies/"""
        return PathManager.userspace() / "strategies"

    @staticmethod
    def extensions_root() -> Path:
        """扩展根目录：userspace/extensions/"""
        return PathManager.userspace() / "extensions"

    @staticmethod
    def system_root() -> Path:
        """系统根目录：userspace/system/"""
        return PathManager.userspace() / "system"

    @staticmethod
    def default_config() -> Path:
        """默认配置目录：core/default_config/"""
        return PathManager.get_root() / "core" / "default_config"

    @staticmethod
    def user_config() -> Path:
        """用户配置目录：userspace/system/config/"""
        return PathManager.system_root() / "config"

    @staticmethod
    def config() -> Path:
        """用户配置目录（同 ``user_config()``）。"""
        return PathManager.user_config()

    @staticmethod
    def system_db() -> Path:
        """DuckDB 等数据库文件目录：userspace/system/db/"""
        return PathManager.system_root() / "db"

    @staticmethod
    def backup() -> Path:
        """备份目录：userspace/system/backup/"""
        return PathManager.system_root() / "backup"

    @staticmethod
    def backup_data() -> Path:
        """备份数据目录：userspace/system/backup/data/"""
        return PathManager.backup() / "data"

    @staticmethod
    def updater() -> Path:
        """应用升级器目录：userspace/system/updater/"""
        return PathManager.system_root() / "updater"

    @staticmethod
    def userspace_ntq() -> Path:
        """NTQ 内部目录：userspace/system/.ntq/"""
        return PathManager.system_root() / ".ntq"

    @staticmethod
    def userspace_tmp() -> Path:
        """临时目录：userspace/system/.ntq/tmp/"""
        return PathManager.userspace_ntq() / "tmp"

    @staticmethod
    def strategy(strategy_name: str) -> Path:
        """策略目录：userspace/strategies/{strategy_name}/"""
        return PathManager.strategies_root() / strategy_name

    @staticmethod
    def strategy_settings(strategy_name: str) -> Path:
        """策略配置：userspace/strategies/{strategy_name}/settings.py"""
        return PathManager.strategy(strategy_name) / "settings.py"

    @staticmethod
    def strategy_results(strategy_name: str) -> Path:
        """策略结果：userspace/strategies/{strategy_name}/results/"""
        return PathManager.strategy(strategy_name) / "results"

    @staticmethod
    def strategy_simulation_enum(strategy_name: str) -> Path:
        """枚举模拟根：.../results/simulations/enum/"""
        return PathManager.strategy_results(strategy_name) / "simulations" / "enum"

    @staticmethod
    def strategy_simulation_price(strategy_name: str) -> Path:
        """价格模拟根：.../results/simulations/price/"""
        return PathManager.strategy_results(strategy_name) / "simulations" / "price"

    @staticmethod
    def strategy_simulation_capital(strategy_name: str) -> Path:
        """资金模拟根：.../results/simulations/capital/"""
        return PathManager.strategy_results(strategy_name) / "simulations" / "capital"

    @staticmethod
    def strategy_scan_results(strategy_name: str) -> Path:
        """扫描结果根：.../results/scan/"""
        return PathManager.strategy_results(strategy_name) / "scan"

    # ========== extensions: Tag ==========

    @staticmethod
    def tags() -> Path:
        """Tag 根目录：userspace/extensions/tags/"""
        return PathManager.extensions_root() / "tags"

    @staticmethod
    def tag_scenario(scenario_name: str) -> Path:
        return PathManager.tags() / scenario_name

    @staticmethod
    def tag_scenario_settings(scenario_name: str) -> Path:
        return PathManager.tag_scenario(scenario_name) / "settings.py"

    @staticmethod
    def tag_scenario_worker(scenario_name: str) -> Path:
        return PathManager.tag_scenario(scenario_name) / "tag_worker.py"

    # ========== extensions: Data Source ==========

    @staticmethod
    def data_source() -> Path:
        """Data Source 根：userspace/extensions/data_source/"""
        return PathManager.extensions_root() / "data_source"

    @staticmethod
    def data_source_mapping() -> Path:
        return PathManager.data_source() / "mapping.py"

    @staticmethod
    def data_source_handlers() -> Path:
        return PathManager.data_source() / "handlers"

    @staticmethod
    def data_source_handler(handler_name: str) -> Path:
        return PathManager.data_source_handlers() / handler_name

    @staticmethod
    def data_source_providers() -> Path:
        return PathManager.data_source() / "providers"

    @staticmethod
    def data_source_provider(provider_name: str) -> Path:
        return PathManager.data_source_providers() / provider_name

    # ========== extensions: Data Contract ==========

    @staticmethod
    def data_contract() -> Path:
        """Data Contract：userspace/extensions/data_contract/"""
        return PathManager.extensions_root() / "data_contract"

    @staticmethod
    def data_contract_mapping() -> Path:
        return PathManager.data_contract() / "mapping.py"

    @staticmethod
    def data_contract_loaders() -> Path:
        return PathManager.data_contract() / "loaders"

    # ========== extensions: Tables / Adapters ==========

    @staticmethod
    def extensions_tables() -> Path:
        """用户自定义表：userspace/extensions/tables/"""
        return PathManager.extensions_root() / "tables"

    @staticmethod
    def adapters() -> Path:
        """扫描适配器：userspace/extensions/adapters/"""
        return PathManager.extensions_root() / "adapters"
