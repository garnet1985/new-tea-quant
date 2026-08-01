"""Catalog implementer: discovery → page DTO for FED.

Calls ``DiscoveryService.discover_strategies`` (strategy core); pagination / row
shaping stay in BFF.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


class StrategyCatalogImplementer:
    def __init__(self) -> None:
        self._DiscoveryService = None

    def lazy_load(self) -> "StrategyCatalogImplementer":
        if self._DiscoveryService is None:
            from core.modules.strategy.core.services.discovery import DiscoveryService
            self._DiscoveryService = DiscoveryService
        return self

    def list_strategies(
        self, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        assert self._DiscoveryService is not None
        discovered = self._DiscoveryService.discover_strategies()
        ordered = sorted(discovered, key=lambda info: str(info.id()))
        total = len(ordered)
        if total == 0:
            return [], 0

        page = max(1, int(page))
        limit = max(1, int(limit))
        start = (page - 1) * limit
        chunk = ordered[start : start + limit]
        return [self._summary(info) for info in chunk], total

    def _summary(self, info: Any) -> Dict[str, Any]:
        meta = info.settings.get("meta") if isinstance(info.settings, dict) else {}
        if not isinstance(meta, dict):
            meta = {}

        details = None
        raw_details = meta.get("details")
        if isinstance(raw_details, dict):
            entry = raw_details.get("entry")
            if isinstance(entry, list) and entry:
                details = {
                    "entry": [
                        str(item).strip()
                        for item in entry
                        if item is not None and str(item).strip()
                    ]
                }
                if not details["entry"]:
                    details = None

        hooks_class = info.hooks_class
        return {
            "key": str(info.key or "").strip(),
            "name": str(info.id()),
            "display_name": str(info.display_name or "").strip(),
            "is_enabled": bool(info.is_enabled),
            "worker_class_name": hooks_class.__name__ if hooks_class is not None else "",
            "folder": str(info.folder),
            "description": self._coerce_meta_text(meta.get("description")),
            "keywords": self._keywords(meta.get("keywords")),
            "details": details,
        }

    @staticmethod
    def _coerce_meta_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            parts = [
                str(item).strip()
                for item in value
                if item is not None and str(item).strip()
            ]
            return "".join(parts)
        return str(value).strip()

    @staticmethod
    def _keywords(raw: Any) -> List[str]:
        if not isinstance(raw, list):
            return []
        out: List[str] = []
        for item in raw:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                out.append(text)
        return out


impl = StrategyCatalogImplementer()
