"""Catalog implementer: discovery → page DTO for FED.

Calls ``Strategy.list_strategy_infos``; pagination / row shaping stay in BFF.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from core.modules.strategy import Strategy


class StrategyCatalogImplementer:
    def lazy_load(self) -> "StrategyCatalogImplementer":
        return self

    def list_strategies(
        self, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        discovered = Strategy.list_strategy_infos(enabled_only=False)
        ordered = sorted(
            discovered, key=lambda info: str(info.get("unique_relative_path") or "")
        )
        total = len(ordered)
        if total == 0:
            return [], 0

        page = max(1, int(page))
        limit = max(1, int(limit))
        start = (page - 1) * limit
        chunk = ordered[start : start + limit]
        return [self._summary(info) for info in chunk], total

    def _summary(self, info: Dict[str, Any]) -> Dict[str, Any]:
        settings = info.get("settings") if isinstance(info.get("settings"), dict) else {}
        meta = settings.get("meta") if isinstance(settings.get("meta"), dict) else {}

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

        return {
            "key": str(info.get("key") or "").strip(),
            "name": str(info.get("unique_relative_path") or "").strip(),
            "display_name": str(info.get("display_name") or "").strip(),
            "is_enabled": bool(info.get("is_enabled")),
            "worker_class_name": str(info.get("hooks_class_name") or "").strip(),
            "folder": str(info.get("folder") or "").strip(),
            "description": self._coerce_meta_text(meta.get("description")),
            "category": str(meta.get("category") or "").strip(),
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
