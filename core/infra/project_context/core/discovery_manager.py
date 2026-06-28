"""Discovery Manager - 配置发现管理器"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .config_manager import ConfigManager
from .path_manager import PathManager

MergeFn = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


class OverridableConfigNotFoundError(FileNotFoundError):
    """core 与 userspace 均未找到有效配置文件。"""


@dataclass(frozen=True)
class DiscoveredConfig:
    domain: str
    config_id: str
    core_path: Optional[Path]
    user_path: Optional[Path]

    @property
    def exists(self) -> bool:
        return self.core_path is not None or self.user_path is not None


class DiscoveryManager:
    """在 NTQ 约定目录结构下发现配置并加载可覆盖配置。"""

    @staticmethod
    def discover_configs(domain: str = "", *, pattern: str = "*.json") -> List[str]:
        """
        扫描 core / userspace 下指定 domain 的 JSON 配置 id（无后缀），并集排序。
        """
        core_dir, user_dir = DiscoveryManager._domain_dirs(domain)
        ids: set[str] = set()
        for directory in (core_dir, user_dir):
            if not directory.is_dir():
                continue
            for path in directory.glob(pattern):
                if path.is_file():
                    ids.add(path.stem)
        return sorted(ids)

    @staticmethod
    def discover_config(domain: str, config_id: str) -> DiscoveredConfig:
        """解析配置在 core / userspace 下的路径，不读取内容。"""
        rel_domain = DiscoveryManager._normalize_domain(domain)
        pid = DiscoveryManager._normalize_config_id(config_id)
        core_dir, user_dir = DiscoveryManager._domain_dirs(rel_domain)
        core_path = DiscoveryManager._config_path(core_dir, pid)
        user_path = DiscoveryManager._config_path(user_dir, pid)
        return DiscoveredConfig(
            domain=rel_domain,
            config_id=pid,
            core_path=core_path if core_path.is_file() else None,
            user_path=user_path if user_path.is_file() else None,
        )

    @staticmethod
    def load_overridable_config(
        domain: str,
        config_id: str,
        *,
        merge_fn: Optional[MergeFn] = None,
        deep_merge_fields: Optional[Set[str]] = None,
        override_fields: Optional[Set[str]] = None,
        file_type: str = "json",
    ) -> Dict[str, Any]:
        """
        加载可覆盖配置。

        - ``merge_fn`` 为 ``None``：``ConfigManager.load_with_defaults``
        - 否则：分别读取 core / user dict，再 ``merge_fn(core, user)``
        """
        discovered = DiscoveryManager.discover_config(domain, config_id)
        rel_domain = discovered.domain
        pid = discovered.config_id
        core_path = discovered.core_path or DiscoveryManager._config_path(
            DiscoveryManager._domain_dirs(rel_domain)[0], pid
        )
        user_path = discovered.user_path or DiscoveryManager._config_path(
            DiscoveryManager._domain_dirs(rel_domain)[1], pid
        )

        if merge_fn is None:
            merged = ConfigManager.load_with_defaults(
                default_path=core_path,
                user_path=user_path,
                deep_merge_fields=deep_merge_fields or set(),
                override_fields=override_fields or set(),
                file_type=file_type,
            )
            if not merged:
                raise OverridableConfigNotFoundError(
                    DiscoveryManager._not_found_message(rel_domain, pid, core_path, user_path)
                )
            return merged

        core_raw = ConfigManager.load_json(core_path) if core_path.is_file() else {}
        user_raw = ConfigManager.load_json(user_path) if user_path.is_file() else {}
        if not isinstance(core_raw, dict):
            core_raw = {}
        if not isinstance(user_raw, dict):
            user_raw = {}

        if not core_raw and not user_raw:
            raise OverridableConfigNotFoundError(
                DiscoveryManager._not_found_message(rel_domain, pid, core_path, user_path)
            )

        if not user_raw:
            return dict(core_raw)
        if not core_raw:
            return dict(user_raw)
        return merge_fn(core_raw, user_raw)

    @staticmethod
    def find_in_tree(
        base_dir: Path,
        key: str,
        config_filename: str = "config.py",
    ) -> Optional[Path]:
        """
        在任意目录树中查找配置（如 data source handlers 下的 config.py）。

        1. ``{base_dir}/{key}/{config_filename}``
        2. 递归 ``*/{key}/{config_filename}`` 与 ``{key}/{config_filename}``
        """
        if not base_dir.exists():
            return None

        direct_path = base_dir / key / config_filename
        if direct_path.is_file():
            return direct_path

        for path in base_dir.rglob(f"*/{key}/{config_filename}"):
            if path.is_file():
                return path

        for path in base_dir.rglob(f"{key}/{config_filename}"):
            if path.is_file():
                return path

        return None

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        rel = str(domain or "").strip().replace("\\", "/").strip("/")
        if rel in ("", "."):
            return ""
        if rel.startswith("..") or "/.." in f"/{rel}/":
            raise ValueError(f"非法 config domain: {domain!r}")
        return rel

    @staticmethod
    def _normalize_config_id(config_id: str) -> str:
        pid = str(config_id or "").strip()
        if not pid or "/" in pid or "\\" in pid or ".." in pid:
            raise ValueError(f"非法 config id: {config_id!r}")
        return pid

    @staticmethod
    def _domain_dirs(domain: str) -> tuple[Path, Path]:
        rel = DiscoveryManager._normalize_domain(domain)
        if not rel:
            return PathManager.get_default_config_root(), PathManager.get_user_config_root()
        return PathManager.get_default_config_root() / rel, PathManager.get_user_config_root() / rel

    @staticmethod
    def _config_path(directory: Path, config_id: str) -> Path:
        return directory / f"{config_id}.json"

    @staticmethod
    def _not_found_message(
        domain: str,
        config_id: str,
        core_path: Path,
        user_path: Path,
    ) -> str:
        dom = domain or "(root)"
        return (
            f"未找到可覆盖配置 {config_id!r}（domain={dom!r}）："
            f"{core_path} 与 {user_path} 均不存在或为空"
        )


__all__ = [
    "DiscoveredConfig",
    "DiscoveryManager",
    "MergeFn",
    "OverridableConfigNotFoundError",
]
