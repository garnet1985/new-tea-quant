"""Tag scenario list for UI (T1-01)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_manager import DataManager
from core.modules.tag.services.discovery import TagDiscoveryHelper


def _iso_dt(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    raw = str(value).strip()
    return raw or None


def _tag_definitions_from_settings(settings: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    tags = settings.get("tags") or []
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


def _execution_mode(settings: Dict[str, Any]) -> str:
    calc = settings.get("calculation") or {}
    if isinstance(calc, dict):
        mode = str(calc.get("execution_mode") or "").strip()
        if mode:
            return mode
    return str(settings.get("execution_mode") or "").strip()


def _update_mode(settings: Dict[str, Any]) -> str:
    calc = settings.get("calculation") or {}
    if isinstance(calc, dict):
        mode = str(calc.get("update_mode") or "").strip().lower()
        if mode:
            return mode
    return str(settings.get("update_mode") or "incremental").strip().lower() or "incremental"


def _recompute(settings: Dict[str, Any]) -> bool:
    calc = settings.get("calculation") or {}
    if isinstance(calc, dict) and "recompute" in calc:
        return bool(calc.get("recompute"))
    return bool(settings.get("recompute"))


def _last_computed_as_of(tag_key: str, tag_svc: Any) -> Optional[str]:
    if tag_svc is None:
        return None
    scenario = tag_svc.load_scenario(tag_key)
    if not scenario:
        return None
    scenario_id = scenario.get("id")
    if scenario_id is None:
        return None
    try:
        defs = tag_svc.get_tag_definitions(int(scenario_id))
    except Exception:
        return None
    def_ids = [int(d["id"]) for d in defs if d.get("id") is not None]
    if not def_ids:
        return None
    return tag_svc.get_max_as_of_date(def_ids)


def _compute_status(
    last_computed_as_of: Optional[str],
    effective_end: str,
    truncation_hint: str,
) -> Tuple[str, str, str]:
    """
    Compare tag MAX(as_of_date) to effective data end from data.json.

    Returns ``(compute_status, compute_status_label, compute_status_hint)``.
    """
    hint = truncation_hint if truncation_hint else ""
    last = str(last_computed_as_of or "").strip()
    end = str(effective_end or "").strip()
    if not last:
        return "needs_recompute", "需要更新", hint
    if end and last < end:
        return "needs_recompute", "需要更新", hint
    return "up_to_date", "已经更新", ""


def _summary(
    item: Any,
    tag_svc: Any,
    *,
    effective_end: str,
    truncation_hint: str,
) -> Dict[str, Any]:
    tag_key = str(item.tag_key)
    settings = item.settings if isinstance(item.settings, dict) else {}
    meta = settings.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    display_name = str(meta.get("display_name") or "").strip()
    description = str(meta.get("description") or "").strip()
    last_computed_as_of = _last_computed_as_of(tag_key, tag_svc)
    compute_status, compute_status_label, compute_status_hint = _compute_status(
        last_computed_as_of,
        effective_end,
        truncation_hint,
    )
    return {
        "name": tag_key,
        "display_name": display_name,
        "is_enabled": bool(settings.get("is_enabled")),
        "description": description,
        "tag_definitions": _tag_definitions_from_settings(settings),
        "last_computed_as_of": last_computed_as_of,
        "compute_status": compute_status,
        "compute_status_label": compute_status_label,
        "compute_status_hint": compute_status_hint,
        "scenario_updated_at": _iso_dt(
            (tag_svc.load_scenario(tag_key) or {}).get("updated_at")
            if tag_svc
            else None
        ),
        "execution_mode": _execution_mode(settings),
        "update_mode": _update_mode(settings),
        "recompute": _recompute(settings),
    }


def fetch_discovered_tags_page(
    page: int,
    limit: int,
) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
    """Paginated tag scenarios; ``page`` is 1-based, sorted by ``name``."""
    from core.modules.data_source.catalog.freshness_probe import get_data_end_meta

    discovered = TagDiscoveryHelper.discover_tags()
    ordered = sorted(discovered.values(), key=lambda d: str(d.tag_key))
    total = len(ordered)
    data_end: Dict[str, Any] = {}
    effective_end = ""
    truncation_hint = ""

    tag_svc = None
    data_manager = None
    try:
        data_manager = DataManager(is_verbose=False)
        data_manager.initialize()
        tag_svc = data_manager.stock.tags
        data_end = get_data_end_meta(data_manager)
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
        _summary(
            item,
            tag_svc,
            effective_end=effective_end,
            truncation_hint=truncation_hint,
        )
        for item in chunk
    ]
    return items, total, data_end
