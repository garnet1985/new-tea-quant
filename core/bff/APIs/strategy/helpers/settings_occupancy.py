"""当前 ``settings.py`` 占用：文件字节 rev + canonical execute 投影。

前端长期只持有草稿；磁盘 rev / freeze 投影按事件向服务端取。
``settings_rev`` 是文件内容 sha256，不是 mtime。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)


class SettingsFileConflict(Exception):
    """``settings.py`` 字节 rev 与客户端 If-Match 不一致。"""

    def __init__(self, occupancy: Dict[str, Any]):
        super().__init__("settings.py 已在别处更新")
        self.occupancy = dict(occupancy or {})


class SettingsOccupancy:
    """读盘 / 投影 / If-Match 校验。"""

    @classmethod
    def settings_path(cls, strategy_name: str) -> Path:
        from core.modules.strategy import Strategy

        return ProjectContext.path.get_strategy_settings_path(
            Strategy.resolve_folder(strategy_name)
        )

    @classmethod
    def file_rev(cls, path: Path) -> str:
        if not path.is_file():
            return ""
        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()

    @classmethod
    def load_disk_settings(cls, path: Path) -> Dict[str, Any]:
        if not path.is_file():
            return {}
        loaded = Discovery.file.load_python_config(path, var_name="settings")
        return dict(loaded) if isinstance(loaded, dict) else {}

    @classmethod
    def execute_settings_of(cls, settings: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return StrategySettings.extract_execute_settings(settings or {})
        except ValueError:
            return {}

    @classmethod
    def occupancy_from_path(cls, path: Path) -> Dict[str, Any]:
        disk_settings = cls.load_disk_settings(path)
        return {
            "settings_rev": cls.file_rev(path),
            "disk_settings": disk_settings,
            "execute_settings": cls.execute_settings_of(disk_settings),
        }

    @classmethod
    def occupancy_from_info(cls, info: Any, disk_settings: Dict[str, Any]) -> Dict[str, Any]:
        path = Path(getattr(info, "settings_file", "") or "")
        rev = cls.file_rev(path) if path else ""
        parsed = dict(disk_settings or {})
        if path.is_file() and not parsed:
            parsed = cls.load_disk_settings(path)
        return {
            "settings_rev": rev,
            "execute_settings": cls.execute_settings_of(parsed),
        }

    @classmethod
    def read(cls, strategy_name: str) -> Dict[str, Any]:
        name = str(strategy_name or "").strip()
        if not name:
            return {
                "settings_rev": "",
                "disk_settings": {},
                "execute_settings": {},
            }
        return cls.occupancy_from_path(cls.settings_path(name))

    @classmethod
    def require_match(
        cls,
        strategy_name: str,
        expected_rev: Optional[str],
        *,
        force: bool = False,
    ) -> Dict[str, Any]:
        occupancy = cls.read(strategy_name)
        if force or expected_rev is None:
            return occupancy
        current = str(occupancy.get("settings_rev") or "")
        if current != str(expected_rev):
            raise SettingsFileConflict(occupancy)
        return occupancy

    @staticmethod
    def parse_if_match(header: Optional[str]) -> str:
        raw = str(header or "").strip()
        if raw.startswith("W/"):
            raw = raw[2:].strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
            raw = raw[1:-1]
        return raw.strip()

    @classmethod
    def expected_rev_from_request(
        cls,
        payload: Optional[Dict[str, Any]] = None,
        *,
        if_match_header: Optional[str] = None,
    ) -> Optional[str]:
        header = cls.parse_if_match(if_match_header)
        if header:
            return header
        if not isinstance(payload, dict):
            return None
        if "settings_rev" not in payload:
            return None
        return str(payload.get("settings_rev") or "")

    @staticmethod
    def conflict_extra(occupancy: Dict[str, Any]) -> Dict[str, Any]:
        occ = dict(occupancy or {})
        return {
            "settings_rev": str(occ.get("settings_rev") or ""),
            "disk_settings": dict(occ.get("disk_settings") or {}),
            "execute_settings": dict(occ.get("execute_settings") or {}),
        }


__all__ = ["SettingsFileConflict", "SettingsOccupancy"]
