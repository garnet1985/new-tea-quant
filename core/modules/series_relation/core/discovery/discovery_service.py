"""扫描 userspace/extensions/series_relation。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.modules.series_relation.core.constants import SETTINGS_FILE_NAME
from core.modules.series_relation.core.discovery.discovered import DiscoveredRelation
from core.modules.series_relation.core.settings.relation_settings import (
    validate_settings,
)

logger = logging.getLogger(__name__)


class DiscoveryService:
    @staticmethod
    def discover(
        *,
        root: Optional[Path] = None,
        declaration_lookup=None,
    ) -> List[DiscoveredRelation]:
        base = root if root is not None else ProjectContext.path.get_series_relation_root()
        if not base.exists():
            return []

        found: List[DiscoveredRelation] = []
        keys_seen: Dict[str, str] = {}

        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not str(d).startswith("_")]
            if "results" in dirnames:
                dirnames.remove("results")
            folder = Path(dirpath)
            settings_file = folder / SETTINGS_FILE_NAME
            if SETTINGS_FILE_NAME not in filenames or not settings_file.is_file():
                continue
            try:
                raw = Discovery.file.load_python_config(
                    settings_file, var_name="settings"
                )
            except Exception as exc:
                logger.warning("无法加载 %s: %s", settings_file, exc)
                continue
            normalized, errors = validate_settings(
                raw, declaration_lookup=declaration_lookup
            )
            if errors or normalized is None:
                logger.warning(
                    "跳过无效 series_relation %s: %s",
                    folder,
                    "; ".join(errors),
                )
                continue
            key = str(normalized["meta"]["key"])
            rel = DiscoveryService._relative(folder, base)
            if key in keys_seen:
                logger.error(
                    "重复 meta.key=%r: %s 与 %s",
                    key,
                    keys_seen[key],
                    rel,
                )
                continue
            keys_seen[key] = rel
            found.append(
                DiscoveredRelation(
                    key=key,
                    display_name=str(normalized["meta"]["display_name"]),
                    relative_path=rel,
                    folder=folder,
                    settings=normalized,
                )
            )

        found.sort(key=lambda item: (item.key, item.relative_path))
        return found

    @staticmethod
    def find(
        key_or_id: str,
        *,
        root: Optional[Path] = None,
        declaration_lookup=None,
    ) -> Optional[DiscoveredRelation]:
        needle = str(key_or_id or "").strip()
        if not needle:
            return None
        for item in DiscoveryService.discover(
            root=root, declaration_lookup=declaration_lookup
        ):
            if item.key == needle or item.relative_path == needle:
                return item
        return None

    @staticmethod
    def _relative(folder: Path, root: Path) -> str:
        try:
            return folder.resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            return folder.name


__all__ = ["DiscoveryService"]
