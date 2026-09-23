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
    def _userspace_state_file() -> Path:
        return PathManager.get_project_root() / ".ntq" / "userspace-path.json"

    @staticmethod
    def _read_userspace_path_from_state() -> Optional[Path]:
        """读 ``.ntq/userspace-path.json``；坏文件或空路径返回 None。"""
        state_file = PathManager._userspace_state_file()
        if not state_file.is_file():
            return None
        try:
            import json

            payload = json.loads(state_file.read_text(encoding="utf-8"))
            state_path = str(payload.get("userspacePath", "")).strip()
            if not state_path:
                return None
            return Path(state_path).expanduser().resolve()
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None

    @staticmethod
    def _assert_userspace_target_writable(target: Path) -> None:
        """安装 / precheck：目标须为目录（或尚不存在），且最近已存在祖先可写。"""
        if target.exists() and not target.is_dir():
            raise ValueError(f"userspace 路径已存在但不是目录: {target}")

        probe = target if target.exists() else target.parent
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        if not probe.exists():
            raise ValueError(f"无法解析 userspace 路径的父目录: {target}")
        if not os.access(probe, os.W_OK | os.X_OK):
            raise PermissionError(f"userspace 路径非法或无权限（不可写）: {target}")

        import tempfile

        try:
            fd, name = tempfile.mkstemp(prefix=".ntq_us_probe_", dir=str(probe))
            os.close(fd)
            os.unlink(name)
        except OSError as exc:
            raise PermissionError(
                f"userspace 路径非法或无权限（不可写）: {target}"
            ) from exc

    @staticmethod
    def get_userspace_root() -> Path:
        """
        获取 userspace 目录的绝对路径（运行时 SOT）。

        优先级：
            1. 环境变量 NEW_TEA_QUANT_USERSPACE_ROOT（最高优先级）
            2. 环境变量 NTQ_USERSPACE_ROOT
            3. 配置文件 .ntq/userspace-path.json
            4. 项目根目录/userspace（默认）

        已配置路径即使目录尚不存在也直接返回，禁止静默回落到项目内 userspace。
        """
        if PathManager._userspace_cache is not None:
            return PathManager._userspace_cache

        for env_path in (
            os.getenv("NEW_TEA_QUANT_USERSPACE_ROOT"),
            os.getenv("NTQ_USERSPACE_ROOT"),
        ):
            text = (env_path or "").strip()
            if text:
                p = Path(text).expanduser().resolve()
                PathManager._userspace_cache = p
                return p

        from_state = PathManager._read_userspace_path_from_state()
        if from_state is not None:
            PathManager._userspace_cache = from_state
            return from_state

        new_path = (PathManager.get_project_root() / "userspace").resolve()
        PathManager._userspace_cache = new_path
        return new_path

    @staticmethod
    def resolve_userspace_target(raw: Optional[Union[str, Path]] = None) -> Path:
        """
        安装 / BFF precheck 专用：规范化并校验可写性，失败抛错。

        - ``raw`` 有内容：``expanduser().resolve()`` 后做可写性检查。
        - ``raw`` 为空：沿用已有 json 指针，否则默认 ``<repo>/userspace``，再校验。
        """
        text = "" if raw is None else str(raw).strip()
        if text:
            target = Path(text).expanduser().resolve()
        else:
            from_state = PathManager._read_userspace_path_from_state()
            if from_state is not None:
                target = from_state
            else:
                target = (PathManager.get_project_root() / "userspace").resolve()

        PathManager._assert_userspace_target_writable(target)
        return target

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
    def get_strategy_simulations_directory(
        strategy_folder_or_rel: Union[str, Path],
    ) -> Path:
        """仿真版本根：``{strategy_root}/results/simulations/``。"""
        return (
            PathManager.get_strategy_results_directory(strategy_folder_or_rel)
            / "simulations"
        )

    @staticmethod
    def get_strategy_simulation_step_directory(
        strategy_folder_or_rel: Union[str, Path],
        version_id: Union[str, int],
        step: str,
    ) -> Path:
        """单步产物目录：``{strategy_root}/results/simulations/{version_id}/{step}/``。"""
        step_key = str(step or "").strip().lower()
        step_dir = {
            "enumerate": "enum",
            "enum": "enum",
            "price_factor": "price",
            "price": "price",
            "portfolio": "portfolio",
        }.get(step_key)
        if step_dir is None:
            raise ValueError(
                f"unsupported simulation step: {step!r} "
                "(expected enum / price / portfolio)"
            )
        vid = str(version_id or "").strip()
        if not vid:
            raise ValueError("version_id 不能为空")
        return (
            PathManager.get_strategy_simulations_directory(strategy_folder_or_rel)
            / vid
            / step_dir
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

    # ========== extensions: Assistant ==========

    @staticmethod
    def get_assistant_root() -> Path:
        """获取 Assistant 根目录：userspace/extensions/assistant/"""
        return PathManager.get_extensions_root() / "assistant"

    @staticmethod
    def get_assistant_providers_directory() -> Path:
        """获取 Assistant providers 目录：.../assistant/providers/"""
        return PathManager.get_assistant_root() / "providers"

    @staticmethod
    def get_assistant_provider_directory(provider_id: str) -> Path:
        """获取指定 Assistant provider 目录：.../assistant/providers/{provider_id}/"""
        return PathManager.get_assistant_providers_directory() / provider_id