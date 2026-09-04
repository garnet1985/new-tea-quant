"""Write settings.py from a version freeze (restore) or current editor (run SOT)."""

from __future__ import annotations

import logging
import os
import pprint
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)
from core.bff.APIs.strategy.helpers.settings_occupancy import (
    SettingsOccupancy,
)
from core.bff.APIs.strategy.helpers.workbench_snapshots import WorkbenchSnapshots

logger = logging.getLogger(__name__)


class WorkbenchApplySettings:
    """Write settings into userspace ``settings.py``.

    Restore: version freeze → file (V2-09).
    Run: current editor payload → file (SOT before simulate).
    """

    @classmethod
    def apply(
        cls,
        *,
        strategy_name: str,
        version: int,
        pretty: bool = False,
        expected_rev: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Snapshot row → validate → backup + atomic write ``settings.py``.

        Success: ``({"applied": True, "strategy_name", "version_id", "settings_rev"}, None)``.
        ``expected_rev`` 与当前文件不一致且未 ``force`` 时抛 ``SettingsFileConflict``。
        """
        name = str(strategy_name or "").strip()
        sid = int(version)
        if not name or sid <= 0:
            return None, "参数无效"

        SettingsOccupancy.require_match(name, expected_rev, force=bool(force))

        row = WorkbenchSnapshots.fetch_by_version(name, sid)
        if not row:
            return None, "快照不存在"

        settings_snapshot = row.get("settings_snapshot")
        if not isinstance(settings_snapshot, dict) or not settings_snapshot:
            return None, "settings 校验失败"

        try:
            ss = StrategySettings.from_dict(settings_snapshot)
            report = ss.validate()
        except Exception as exc:
            logger.exception("apply-settings validate failed strategy=%s", name)
            return None, f"settings 校验失败: {exc}"

        if not report.is_usable():
            return None, StrategySettings.format_validation_error(report)

        fp_err = cls._verify_settings_fingerprint(name, sid, settings_snapshot)
        if fp_err:
            return None, fp_err

        normalized = ss.to_dict()

        try:
            cls._backup_settings_file(name)
            cls._write_settings_py(name, normalized, pretty)
        except Exception as exc:
            logger.exception(
                "apply-settings 写盘失败 strategy=%s version=%s", name, sid
            )
            return None, f"写盘失败: {exc}"

        occupancy = SettingsOccupancy.read(name)
        return (
            {
                "applied": True,
                "strategy_name": name,
                "version_id": f"v{sid}",
                "settings_rev": occupancy["settings_rev"],
                "disk_settings": occupancy["disk_settings"],
                "execute_settings": occupancy["execute_settings"],
            },
            None,
        )

    @classmethod
    def persist_editor_settings(
        cls,
        *,
        strategy_name: str,
        settings: Dict[str, Any],
        pretty: bool = True,
        expected_rev: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """校验草稿后按原样写 ``settings.py``（不展开默认值）。

        成功：``({settings_rev, disk_settings, execute_settings}, None)``。
        空 payload：``(None, None)``（不写盘）。
        ``expected_rev`` 不匹配且未 ``force`` 时抛 ``SettingsFileConflict``。
        """
        name = str(strategy_name or "").strip()
        if not name:
            return None, "参数无效"
        if not isinstance(settings, dict) or not settings:
            return None, None

        SettingsOccupancy.require_match(name, expected_rev, force=bool(force))

        try:
            ss = StrategySettings.from_dict(settings)
            report = ss.validate()
        except Exception as exc:
            logger.exception("persist editor settings validate failed strategy=%s", name)
            return None, f"settings 校验失败: {exc}"

        if not report.is_usable():
            return None, StrategySettings.format_validation_error(report)

        try:
            cls._backup_settings_file(name)
            cls._write_settings_py(name, dict(settings), pretty)
        except Exception as exc:
            logger.exception("persist editor settings 写盘失败 strategy=%s", name)
            return None, f"写盘失败: {exc}"
        occupancy = SettingsOccupancy.read(name)
        return (
            {
                "settings_rev": occupancy["settings_rev"],
                "disk_settings": occupancy["disk_settings"],
                "execute_settings": occupancy["execute_settings"],
            },
            None,
        )

    @classmethod
    def _verify_settings_fingerprint(
        cls,
        strategy_name: str,
        version: int,
        settings_snapshot: Dict[str, Any],
    ) -> Optional[str]:
        """恢复前 round-trip：快照 execute_fp 须与 registry 一致。"""
        from core.modules.strategy.core.services.artifacts import ArtifactStore
        from core.modules.strategy.core.services.artifacts.version_meta import (
            VersionMetaStore,
        )
        from core.modules.strategy.core.services.discovery import DiscoveryService
        from core.modules.strategy.core.services.fingerprint import (
            FingerprintCalculator,
        )

        folder = DiscoveryService.resolve_strategy_folder(strategy_name)
        root = ArtifactStore.simulations_root(folder)
        entry = VersionMetaStore.get_registry_entry(root, str(int(version)))
        expected = str((entry or {}).get("execute_fp") or "").strip()
        if not expected:
            return None

        archive = VersionMetaStore.read_archive_context(root, str(int(version)))
        try:
            computed = FingerprintCalculator.to_execute_fingerprint(
                StrategySettings.from_dict(settings_snapshot),
                archive.get("entity_ids") or [],
            )
        except ValueError as exc:
            return f"配置快照无法计算指纹: {exc}"
        if computed != expected:
            return "配置快照与 version 指纹不一致"
        return None

    @staticmethod
    def _settings_path(strategy_name: str) -> Path:
        return SettingsOccupancy.settings_path(strategy_name)

    @classmethod
    def _backup_settings_file(cls, strategy_name: str) -> None:
        settings_file = cls._settings_path(strategy_name)
        if settings_file.is_file():
            backup_path = settings_file.with_suffix(settings_file.suffix + ".bak")
            backup_path.write_text(
                settings_file.read_text(encoding="utf-8"), encoding="utf-8"
            )

    @classmethod
    def _write_settings_py(
        cls, strategy_name: str, settings: Dict[str, Any], pretty: bool
    ) -> None:
        settings_file = cls._settings_path(strategy_name)
        if pretty:
            literal = pprint.pformat(dict(settings or {}), width=88, sort_dicts=False)
        else:
            literal = repr(dict(settings or {}))
        content = (
            "# Restored / persisted by Strategy Workbench into userspace settings.py.\n"
            "# Manual edits are allowed; next save from Workbench may reformat this file.\n\n"
            f"settings = {literal}\n"
        )
        if pretty:
            content = cls._format_settings_py(content)
        cls._atomic_write_text(settings_file, content)

    @staticmethod
    def _format_settings_py(content: str) -> str:
        """Best-effort Black format so Workbench writes match hand-edited settings style."""
        try:
            import black
        except Exception:
            return content
        try:
            return black.format_str(
                content,
                mode=black.Mode(line_length=100, string_normalization=True),
            )
        except Exception:
            return content

    @staticmethod
    def _atomic_write_text(
        target_path: Path, content: str, encoding: str = "utf-8"
    ) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", encoding=encoding, dir=target_path.parent, delete=False
        ) as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)
        os.replace(str(temp_path), str(target_path))


__all__ = ["WorkbenchApplySettings"]
