"""Apply snapshot settings → userspace ``settings.py`` (V2-09)."""

from __future__ import annotations

import logging
import os
import pprint
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional, Tuple

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)
from core.bff.APIs.strategy.helpers.workbench_snapshots import WorkbenchSnapshots

logger = logging.getLogger(__name__)


class WorkbenchApplySettings:
    """Write a snapshot's effective settings into userspace ``settings.py``."""

    @classmethod
    def apply(
        cls,
        *,
        strategy_name: str,
        version: int,
        pretty: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Snapshot row → validate → backup + atomic write ``settings.py``.

        Success: ``({"applied": True, "strategy_name", "version_id"}, None)``.
        """
        name = str(strategy_name or "").strip()
        sid = int(version)
        if not name or sid <= 0:
            return None, "参数无效"

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
            return None, cls._format_validation_error(report)

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

        return (
            {
                "applied": True,
                "strategy_name": name,
                "version_id": f"v{sid}",
            },
            None,
        )

    @staticmethod
    def _format_validation_error(report: Any) -> str:
        errors = list(getattr(report, "errors", None) or [])
        if not errors:
            return "settings 校验失败"
        first = errors[0]
        if isinstance(first, dict):
            field = str(first.get("field") or first.get("path") or "").strip()
            msg = str(first.get("message") or first.get("msg") or first).strip()
            if field and msg:
                return f"settings 校验失败: {field}: {msg}"
            if msg:
                return f"settings 校验失败: {msg}"
        return f"settings 校验失败: {first}"

    @classmethod
    def _verify_settings_fingerprint(
        cls,
        strategy_name: str,
        version: int,
        settings_snapshot: Dict[str, Any],
    ) -> Optional[str]:
        """恢复前 round-trip：快照 settings_fp 须与 registry 一致。"""
        from core.modules.strategy.core.services.artifacts import ArtifactStore
        from core.modules.strategy.core.services.artifacts.version_meta import (
            VersionMetaStore,
        )
        from core.modules.strategy.core.services.discovery import DiscoveryService
        from core.modules.strategy.core.services.simulation_cache.fingerprints import (
            FingerprintCalculator,
        )

        folder = DiscoveryService.resolve_strategy_folder(strategy_name)
        root = ArtifactStore.simulations_root(folder)
        entry = VersionMetaStore.get_registry_entry(root, str(int(version)))
        expected = str((entry or {}).get("settings_fp") or "").strip()
        if not expected:
            return None

        effective = VersionMetaStore.read_effective_settings(root, str(int(version))) or {}
        entity_ids = [
            str(x).strip()
            for x in (effective.get("entity_ids") or [])
            if str(x).strip()
        ]
        computed = FingerprintCalculator.to_effective_settings_fingerprint(
            StrategySettings.from_dict(settings_snapshot),
            entity_ids,
        )
        if computed != expected:
            return "配置快照与 version 指纹不一致"
        return None

    @staticmethod
    def _settings_path(strategy_name: str) -> Path:
        from core.modules.strategy import Strategy

        return ProjectContext.path.get_strategy_settings_path(
            Strategy.resolve_folder(strategy_name)
        )

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
            "# Auto-generated by Strategy Workbench (apply snapshot version to userspace).\n"
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
