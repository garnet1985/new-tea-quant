"""Path Manager - 路径管理器"""
from pathlib import Path
from typing import Optional, Union
import logging
import os
import sys

logger = logging.getLogger(__name__)


class PathManager:
    """路径管理器 - 提供项目常用路径的快捷访问"""

    _root_cache: Optional[Path] = None
    _userspace_cache: Optional[Path] = None

    @staticmethod
    def clear_userspace_cache() -> None:
        """清理 userspace 路径缓存（当路径变化后强制重新计算）"""
        PathManager._userspace_cache = None

    @staticmethod
    def get_project_root() -> Path:
        """获取项目根目录的绝对路径（通过.git、pyproject.toml等标记定位）"""
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
    def get_venv_python() -> Path:
        """项目 ``venv`` 解释器路径（文件未必存在；不 ``resolve()``）。"""
        root = PathManager.get_project_root()
        if os.name == "nt":
            return root / "venv" / "Scripts" / "python.exe"
        return root / "venv" / "bin" / "python"

    @staticmethod
    def get_sys_python() -> Path:
        """系统解释器（venv 外的 base interpreter；不在 venv 内时即当前进程）。"""
        base_exe = getattr(sys, "_base_executable", "") or ""
        if base_exe:
            p = Path(base_exe)
            if p.is_file():
                return p
        prefix = Path(sys.base_prefix)
        if os.name == "nt":
            candidates = (prefix / "python.exe", prefix / "Scripts" / "python.exe")
        else:
            candidates = (prefix / "bin" / "python3", prefix / "bin" / "python")
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return Path(sys.executable)

    @staticmethod
    def get_python(*, allow_sys_fallback: bool = True) -> Path:
        """可执行解释器：优先 ``venv``；没有则按 ``allow_sys_fallback`` 回退系统解释器。"""
        vpy = PathManager.get_venv_python()
        if vpy.is_file():
            return vpy
        if allow_sys_fallback:
            return PathManager.get_sys_python()
        raise FileNotFoundError(f"venv python not found: {vpy}")

    @staticmethod
    def get_core_root() -> Path:
        """获取 core 目录的绝对路径"""
        return PathManager.get_project_root() / "core"

    @staticmethod
    def get_userspace_root() -> Path:
        """
        获取 userspace 目录的绝对路径（支持环境变量覆盖）

        优先级：
            1. 环境变量 NEW_TEA_QUANT_USERSPACE_ROOT（最高优先级）
            2. 环境变量 NTQ_USERSPACE_ROOT
            3. 配置文件 .ntq/userspace-path.json
            4. 项目根目录/userspace（默认）
        """
        if PathManager._userspace_cache is not None:
            return PathManager._userspace_cache

        root = PathManager.get_project_root()

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
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass

        new_path = root / "userspace"
        PathManager._userspace_cache = new_path
        return new_path

    @staticmethod
    def get_strategies_root() -> Path:
        """获取策略根目录：userspace/strategies/"""
        return PathManager.get_userspace_root() / "strategies"

    @staticmethod
    def get_extensions_root() -> Path:
        """获取扩展根目录：userspace/extensions/"""
        return PathManager.get_userspace_root() / "extensions"

    @staticmethod
    def get_system_root() -> Path:
        """获取系统根目录：userspace/system/"""
        return PathManager.get_userspace_root() / "system"

    @staticmethod
    def get_default_config_root() -> Path:
        """获取默认配置目录：core/default_config/"""
        return PathManager.get_project_root() / "core" / "default_config"

    @staticmethod
    def get_user_config_root() -> Path:
        """获取用户配置目录：userspace/system/config/"""
        return PathManager.get_system_root() / "config"

    # ========== 系统目录 ==========

    @staticmethod
    def get_system_db_directory() -> Path:
        """获取系统数据库目录：userspace/system/db/"""
        return PathManager.get_system_root() / "db"

    @staticmethod
    def get_backup_directory() -> Path:
        """获取备份目录：userspace/system/backup/"""
        return PathManager.get_system_root() / "backup"

    @staticmethod
    def get_backup_data_directory() -> Path:
        """获取备份数据目录：userspace/system/backup/data/"""
        return PathManager.get_backup_directory() / "data"

    @staticmethod
    def get_updater_directory() -> Path:
        """获取应用升级器目录：userspace/system/updater/"""
        return PathManager.get_system_root() / "updater"

    @staticmethod
    def get_userspace_ntq_directory() -> Path:
        """获取 NTQ 内部目录：userspace/.ntq/"""
        return PathManager.get_userspace_root() / ".ntq"

    @staticmethod
    def get_userspace_tmp_directory() -> Path:
        """获取临时目录：userspace/.ntq/tmp/"""
        return PathManager.get_userspace_ntq_directory() / "tmp"

    # ========== 策略相关路径 ==========

    @staticmethod
    def coerce_strategy_folder(strategy_folder_or_rel: Union[str, Path]) -> Path:
        """Normalize a strategy root.

        - Absolute path → discovered strategy folder (preferred after discovery).
        - Relative name/path → ``userspace/strategies/{rel}`` (bootstrap / API id only).
        """
        if strategy_folder_or_rel is None:
            raise ValueError("strategy folder/path 不能为空")
        p = Path(strategy_folder_or_rel)
        if p.is_absolute():
            return p
        rel = str(strategy_folder_or_rel).strip().replace("\\", "/").lstrip("/")
        if not rel:
            raise ValueError("strategy folder/path 不能为空")
        return PathManager.get_strategies_root() / rel

    @staticmethod
    def get_strategy_directory(strategy_folder_or_rel: Union[str, Path]) -> Path:
        """策略根目录：优先绝对 discovered folder，否则拼到 userspace/strategies/。"""
        return PathManager.coerce_strategy_folder(strategy_folder_or_rel)

    @staticmethod
    def get_strategy_settings_path(strategy_folder_or_rel: Union[str, Path]) -> Path:
        """策略 settings.py：``{strategy_root}/settings.py``。"""
        return PathManager.get_strategy_directory(strategy_folder_or_rel) / "settings.py"

    @staticmethod
    def get_strategy_results_directory(strategy_folder_or_rel: Union[str, Path]) -> Path:
        """策略结果目录：``{strategy_root}/results/``。"""
        return PathManager.get_strategy_directory(strategy_folder_or_rel) / "results"

    @staticmethod
    def get_strategy_simulation_enum_directory(
        strategy_folder_or_rel: Union[str, Path],
    ) -> Path:
        """枚举模拟结果：``{strategy_root}/results/simulations/enum/``。"""
        return (
            PathManager.get_strategy_results_directory(strategy_folder_or_rel)
            / "simulations"
            / "enum"
        )

    @staticmethod
    def get_strategy_simulation_price_directory(
        strategy_folder_or_rel: Union[str, Path],
    ) -> Path:
        """价格模拟结果：``{strategy_root}/results/simulations/price/``。"""
        return (
            PathManager.get_strategy_results_directory(strategy_folder_or_rel)
            / "simulations"
            / "price"
        )

    @staticmethod
    def get_strategy_simulation_portfolio_directory(
        strategy_folder_or_rel: Union[str, Path],
    ) -> Path:
        """组合模拟结果：``{strategy_root}/results/simulations/portfolio/``。"""
        return (
            PathManager.get_strategy_results_directory(strategy_folder_or_rel)
            / "simulations"
            / "portfolio"
        )

    @staticmethod
    def get_strategy_scan_results_directory(
        strategy_folder_or_rel: Union[str, Path],
    ) -> Path:
        """扫描结果：``{strategy_root}/results/scan/``。"""
        return PathManager.get_strategy_results_directory(strategy_folder_or_rel) / "scan"

    # ========== extensions: Tag ==========

    @staticmethod
    def get_tags_root() -> Path:
        """获取 Tag 根目录：userspace/extensions/tags/"""
        return PathManager.get_extensions_root() / "tags"

    @staticmethod
    def get_tag_scenario_directory(scenario_name: str) -> Path:
        """获取指定 Tag scenario 的目录：userspace/extensions/tags/{scenario_name}/"""
        return PathManager.get_tags_root() / scenario_name

    @staticmethod
    def get_tag_scenario_settings_path(scenario_name: str) -> Path:
        """获取指定 Tag scenario 的配置文件：.../tags/{scenario_name}/settings.py"""
        return PathManager.get_tag_scenario_directory(scenario_name) / "settings.py"

    @staticmethod
    def get_tag_scenario_worker_path(scenario_name: str) -> Path:
        """获取指定 Tag scenario 的 hooks 文件：.../tags/{scenario_name}/tag.py"""
        return PathManager.get_tag_scenario_directory(scenario_name) / "tag.py"

    # ========== extensions: Data Source ==========

    @staticmethod
    def get_data_source_root() -> Path:
        """获取 Data Source 根目录：userspace/extensions/data_source/"""
        return PathManager.get_extensions_root() / "data_source"

    @staticmethod
    def get_data_source_mapping_path() -> Path:
        """获取 Data Source mapping 文件：.../data_source/mapping.py"""
        return PathManager.get_data_source_root() / "mapping.py"

    @staticmethod
    def get_data_source_handlers_directory() -> Path:
        """获取 Data Source handlers 目录：.../data_source/handlers/"""
        return PathManager.get_data_source_root() / "handlers"

    @staticmethod
    def get_data_source_handler_directory(handler_name: str) -> Path:
        """获取指定 Data Source handler 的目录：.../data_source/handlers/{handler_name}/"""
        return PathManager.get_data_source_handlers_directory() / handler_name

    @staticmethod
    def get_data_source_providers_directory() -> Path:
        """获取 Data Source providers 目录：.../data_source/providers/"""
        return PathManager.get_data_source_root() / "providers"

    @staticmethod
    def get_data_source_provider_directory(provider_name: str) -> Path:
        """获取指定 Data Source provider 的目录：.../data_source/providers/{provider_name}/"""
        return PathManager.get_data_source_providers_directory() / provider_name

    # ========== extensions: Data Contract ==========

    @staticmethod
    def get_data_contract_root() -> Path:
        """获取 Data Contract 根目录：userspace/extensions/data_contract/"""
        return PathManager.get_extensions_root() / "data_contract"

    @staticmethod
    def get_data_contract_mapping_path() -> Path:
        """获取 Data Contract mapping 文件：.../data_contract/mapping.py"""
        return PathManager.get_data_contract_root() / "mapping.py"

    @staticmethod
    def get_data_contract_loaders_directory() -> Path:
        """获取 Data Contract loaders 目录：.../data_contract/loaders/"""
        return PathManager.get_data_contract_root() / "loaders"

    # ========== extensions: Tables / Adapters ==========

    @staticmethod
    def get_extensions_tables_directory() -> Path:
        """获取用户自定义表目录：userspace/extensions/tables/"""
        return PathManager.get_extensions_root() / "tables"

    @staticmethod
    def get_adapters_directory() -> Path:
        """获取扫描适配器目录：userspace/extensions/adapters/"""
        return PathManager.get_extensions_root() / "adapters"