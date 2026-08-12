"""Tag scenario list for UI (T1-01)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_manager import DataManager
from core.modules.tag.core.services.discovery import DiscoveryService
from core.modules.tag.core.services.discovery.data.discovered_tag import DiscoveredTagInfo


class TagCatalog:
    """UI 列表：discovery + freshness 摘要。"""

    @classmethod
    def fetch_page(
        cls,
        page: int,
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """Paginated tag scenarios; ``page`` is 1-based, sorted by ``name``."""
        from core.modules.data_source import DataSourceManager

        discovered = DiscoveryService.discover_tags()
        ordered = sorted(discovered, key=lambda d: str(d.id()))
        total = len(ordered)
        data_end: Dict[str, Any] = {}
        effective_end = ""
        truncation_hint = ""

        tag_svc = None
        try:
            data_manager = DataManager(is_verbose=False)
            data_manager.initialize()
            tag_svc = data_manager.stock.tags
            data_end = DataSourceManager.get_data_end_meta(data_manager)
            effective_end = str(data_end.get("effective_end_date") or "").strip()
            if data_end.get("is_end_date_truncated"):
                truncation_hint = str(data_end.get("truncation_hint") or "").strip()
        except Exception:
            tag_svc = None

        if total == 0:
            return [], 0, data_end

        page = max(1, int(page))
        limit = max(1, int(limit))
        start = (page - 1) * limit
        chunk = ordered[start : start + limit]

        items = [
            cls._summary(
                item,
                tag_svc,
                effective_end=effective_end,
                truncation_hint=truncation_hint,
            )
            for item in chunk
        ]
        return items, total, data_end

    @classmethod
    def _summary(
        cls,
        item: DiscoveredTagInfo,
        tag_svc: Any,
        *,
        effective_end: str,
        truncation_hint: str,
    ) -> Dict[str, Any]:
        tag_key = str(item.id())
        settings = item.settings if isinstance(item.settings, dict) else {}
        meta = settings.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        display_name = str(meta.get("display_name") or "").strip()
        description = str(meta.get("description") or "").strip()
        last_computed_as_of = cls._last_computed_as_of(tag_key, tag_svc)
        # 水位可能标成 data.json 配置日（非交易日）；展示/状态按有效交易日截断对齐
        end = str(effective_end or "").strip()
        last = str(last_computed_as_of or "").strip()
        if end and last and last > end:
            last_computed_as_of = end
        compute_status, compute_status_label, compute_status_hint = cls._compute_status(
            last_computed_as_of,
            effective_end,
            truncation_hint,
        )
        return {
            "name": tag_key,
            "display_name": display_name,
            "is_enabled": bool(settings.get("is_enabled")),
            "description": description,
            "tag_definitions": cls._tag_definitions_from_settings(settings),
            "last_computed_as_of": last_computed_as_of,
            "compute_status": compute_status,
            "compute_status_label": compute_status_label,
            "compute_status_hint": compute_status_hint,
            "scenario_updated_at": cls._iso_dt(
                (tag_svc.load_scenario(tag_key) or {}).get("updated_at")
                if tag_svc
                else None
            ),
            "execution_mode": cls._execution_mode(settings),
            "update_mode": cls._update_mode(settings),
            "recompute": cls._recompute(settings),
        }

    @classmethod
    def _iso_dt(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat(sep=" ", timespec="seconds")
        raw = str(value).strip()
        return raw or None

    @classmethod
    def _tag_definitions_from_settings(
        cls, settings: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        tags = settings.get("tag_definitions") or []
        if not isinstance(tags, list):
            return out
        for item in tags:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            display = str(item.get("display_name") or name).strip()
            out.append({"name": name, "display_name": display})
        return out

    @classmethod
    def _execution_mode(cls, settings: Dict[str, Any]) -> str:
        calc = settings.get("calculation") or {}
        if not isinstance(calc, dict):
            return ""
        execution = calc.get("execution") or {}
        if not isinstance(execution, dict):
            return ""
        return str(execution.get("mode") or "").strip()

    @classmethod
    def _update_mode(cls, settings: Dict[str, Any]) -> str:
        calc = settings.get("calculation") or {}
        if not isinstance(calc, dict):
            return "incremental"
        mode = str(calc.get("update_mode") or "").strip().lower()
        return mode or "incremental"

    @classmethod
    def _recompute(cls, settings: Dict[str, Any]) -> bool:
        calc = settings.get("calculation") or {}
        if not isinstance(calc, dict):
            return False
        return bool(calc.get("recompute"))

    @classmethod
    def _last_computed_as_of(cls, tag_key: str, tag_svc: Any) -> Optional[str]:
        """列表「最后计算至」：优先 ``sys_tag_calc_progress``，不是 MAX(as_of)。

        变化日写入的 tag（如利率 stance）可能很久才落一条 value；用 max(as_of)
        会误报「需要更新」。取各实体 ``last_calculated_end`` 的最小值作为保守 frontier。

        progress 为空时（旧 refresh 跑完未写水位）回退 ``MAX(as_of)``，避免列表永久「需要更新」。
        """
        if tag_svc is None:
            return None
        try:
            progress = tag_svc.get_entity_calc_progress(tag_key) or {}
        except Exception:
            progress = {}
        ends = [str(v).strip() for v in progress.values() if str(v or "").strip()]
        if ends:
            return min(ends)
        return cls._max_as_of_fallback(tag_key, tag_svc)

    @classmethod
    def _max_as_of_fallback(cls, tag_key: str, tag_svc: Any) -> Optional[str]:
        scenario = tag_svc.load_scenario(tag_key)
        if not scenario or scenario.get("id") is None:
            return None
        try:
            defs = tag_svc.get_tag_definitions(int(scenario["id"]))
        except Exception:
            return None
        def_ids = [int(d["id"]) for d in defs if d.get("id") is not None]
        if not def_ids:
            return None
        try:
            return tag_svc.get_max_as_of_date(def_ids)
        except Exception:
            return None

    @classmethod
    def _compute_status(
        cls,
        last_computed_as_of: Optional[str],
        effective_end: str,
        truncation_hint: str,
    ) -> Tuple[str, str, str]:
        hint = truncation_hint if truncation_hint else ""
        last = str(last_computed_as_of or "").strip()
        end = str(effective_end or "").strip()
        if not last:
            return "needs_recompute", "需要更新", hint
        if end and last < end:
            return "needs_recompute", "需要更新", hint
        return "up_to_date", "已经更新", ""


__all__ = ["TagCatalog"]
