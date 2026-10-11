"""Tag 可视化读模型（T1-07）。

把 ``sys_data_tag_value`` 收成三种视图：
- 时序全局：按标签展示名分列的区间（甘特）；取值只留在悬停
- 时序按实体：实体当前标签；指定 entity_id 时改为该实体的区间
- 非时序：最新一条 JSON 的展示形状（类别表 / 字段表 / 标量）
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.bff.shared.client_log import log_degraded
from core.modules.data_manager import DataManager
from core.modules.data_manager.core.data_services.stock.sub_services.tag_service import (
    TagDataService,
)
from core.modules.tag.core.engines.global_based.constants import GLOBAL_ENTITY_ID
from core.modules.tag.core.engines.shared.tag_settings.data_settings import DataSettings
from core.modules.tag.core.services.discovery import DiscoveryService

_VALUE_TABLE = "sys_data_tag_value"
_NAME_CHUNK = 400

_LATEST_SQL = """
SELECT entity_id, as_of_date, json_value, tag_name, tag_display_name
FROM (
    SELECT
        tv.entity_id,
        tv.as_of_date,
        tv.json_value,
        td.name AS tag_name,
        td.display_name AS tag_display_name,
        ROW_NUMBER() OVER (
            PARTITION BY tv.entity_id, tv.tag_definition_id
            ORDER BY tv.as_of_date DESC
        ) AS rn
    FROM sys_data_tag_value tv
    INNER JOIN sys_data_tag_definition td ON tv.tag_definition_id = td.id
    INNER JOIN sys_data_tag_scenario sc ON td.scenario_id = sc.id
    WHERE sc.name = %s
) t
WHERE rn = 1
ORDER BY entity_id, tag_name
"""

_SERIES_SQL = """
SELECT
    tv.entity_id,
    tv.as_of_date,
    tv.start_date,
    tv.end_date,
    tv.json_value,
    td.name AS tag_name,
    td.display_name AS tag_display_name
FROM sys_data_tag_value tv
INNER JOIN sys_data_tag_definition td ON tv.tag_definition_id = td.id
INNER JOIN sys_data_tag_scenario sc ON td.scenario_id = sc.id
WHERE sc.name = %s AND tv.entity_id = %s
ORDER BY td.name ASC, tv.as_of_date ASC
"""


class TagVisualization:
    """按 scenario 路由组装可视化 payload。"""

    @classmethod
    def fetch(cls, tag_key: str, entity_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """标签不在 discovery 中时返回 None。"""
        info = cls._find(tag_key)
        if info is None:
            return None
        settings = info.settings if isinstance(info.settings, dict) else {}
        route = DataSettings(raw_settings=settings).base_route()
        display_name = str(info.display_name or "").strip() or str(info.id())
        wanted = str(entity_id or "").strip()
        payload: Dict[str, Any] = {
            "tag_key": str(info.id()),
            "display_name": display_name,
            "route": route,
            "horizon_end": "",
            "entities": [],
            "intervals": [],
            "snapshots": [],
        }
        data_manager = DataManager(is_verbose=False)
        data_manager.initialize()
        tag_svc = data_manager.stock.tags
        scenario_name = str(info.id())
        if route == "per_entity" and not wanted:
            latest = cls._load_latest(tag_svc, scenario_name)
            names = cls._stock_names(data_manager, [row["entity_id"] for row in latest])
            payload["entities"] = build_entity_rows(latest, names)
            return payload
        series_entity = wanted or GLOBAL_ENTITY_ID
        points = cls._load_series(tag_svc, scenario_name, series_entity)
        horizon = cls._horizon(tag_svc, scenario_name, series_entity, points)
        payload["horizon_end"] = horizon
        payload["lanes"] = definition_lanes(settings)
        if route == "non_time_series":
            payload["snapshots"] = build_snapshots(points)
            return payload
        payload["intervals"] = build_intervals(points, horizon)
        return payload

    @staticmethod
    def _find(tag_key: str):
        needle = str(tag_key or "").strip().strip("/")
        if not needle:
            return None
        for info in DiscoveryService.discover_tags():
            if info.id() == needle or info.key == needle:
                return info
        return None

    @classmethod
    def _load_latest(cls, tag_svc: Any, scenario_name: str) -> List[Dict[str, Any]]:
        rows = cls._query(tag_svc, _LATEST_SQL, (scenario_name,))
        points: List[Dict[str, Any]] = []
        for row in rows:
            point = normalize_point(row)
            if point is not None:
                points.append(point)
        return points

    @classmethod
    def _load_series(
        cls, tag_svc: Any, scenario_name: str, entity_id: str
    ) -> List[Dict[str, Any]]:
        rows = cls._query(tag_svc, _SERIES_SQL, (scenario_name, entity_id))
        points: List[Dict[str, Any]] = []
        for row in rows:
            point = normalize_point(row)
            if point is not None:
                points.append(point)
        return points

    @staticmethod
    def _query(tag_svc: Any, sql: str, params: Tuple[Any, ...]) -> List[Dict[str, Any]]:
        rows = tag_svc.db.execute_sync_query_for_table(_VALUE_TABLE, sql, params)
        return list(rows or [])

    @classmethod
    def _horizon(
        cls,
        tag_svc: Any,
        scenario_name: str,
        entity_id: str,
        points: List[Dict[str, Any]],
    ) -> str:
        progress: Dict[str, str] = {}
        try:
            progress = tag_svc.get_entity_calc_progress(scenario_name) or {}
        except Exception as exc:
            log_degraded("tag.visualization.progress", exc, scenario_name)
        horizon = str(progress.get(entity_id) or "").strip()
        if not horizon and progress:
            ends = [str(value).strip() for value in progress.values() if str(value or "").strip()]
            horizon = max(ends) if ends else ""
        as_ofs = [str(point.get("as_of") or "") for point in points if point.get("as_of")]
        if as_ofs and (not horizon or max(as_ofs) > horizon):
            return max(as_ofs)
        return horizon

    @classmethod
    def _stock_names(cls, data_manager: Any, entity_ids: List[str]) -> Dict[str, str]:
        ids = []
        seen = set()
        for raw in entity_ids:
            eid = str(raw or "").strip()
            if not eid or eid == GLOBAL_ENTITY_ID or eid in seen:
                continue
            seen.add(eid)
            ids.append(eid)
        if not ids:
            return {}
        try:
            model = data_manager.get_table("sys_data_stock_list")
        except Exception as exc:
            log_degraded("tag.visualization.stockList", exc)
            return {}
        if model is None:
            return {}
        names: Dict[str, str] = {}
        for start in range(0, len(ids), _NAME_CHUNK):
            chunk = ids[start : start + _NAME_CHUNK]
            try:
                rows = model.load_by_ids(chunk) or []
            except Exception as exc:
                log_degraded("tag.visualization.stockNames", exc)
                continue
            for row in rows:
                eid = str(row.get("id") or "").strip()
                name = str(row.get("name") or "").strip()
                if eid and name:
                    names[eid] = name
        return names


def normalize_point(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """DB 行 → 可视化点。日期统一 YYYYMMDD，json_value 解开 ``value``。"""
    if not isinstance(row, dict):
        return None
    as_of = _yyyymmdd(row.get("as_of_date"))
    if not as_of:
        return None
    tag_name = str(row.get("tag_name") or "").strip()
    display = str(row.get("tag_display_name") or tag_name).strip() or tag_name
    return {
        "entity_id": str(row.get("entity_id") or "").strip(),
        "as_of": as_of,
        "start_date": _yyyymmdd(row.get("start_date")) or "",
        "end_date": _yyyymmdd(row.get("end_date")) or "",
        "tag_name": tag_name,
        "tag_display_name": display,
        "value": decode_value(row.get("json_value")),
    }


def decode_value(raw: Any) -> Any:
    """``json_value`` 可能是 JSON 字符串或已解析对象；业务值在 ``value`` 键。"""
    payload = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text
    if isinstance(payload, dict) and "value" in payload:
        return payload.get("value")
    return payload


def definition_lanes(settings: Dict[str, Any]) -> List[str]:
    """settings 里的标签展示名，顺序就是甘特纵轴。"""
    raw = settings.get("tag_definitions") if isinstance(settings, dict) else None
    lanes: List[str] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("display_name") or item.get("name") or "").strip()
        if label and label not in lanes:
            lanes.append(label)
    return lanes


def build_entity_rows(
    latest: List[Dict[str, Any]],
    names: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """每个实体一行：当前标签（最近一个变化日）和悬停用的取值。"""
    lookup = names or {}
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for point in latest:
        eid = str(point.get("entity_id") or "").strip()
        if not eid or eid == GLOBAL_ENTITY_ID:
            continue
        grouped[eid].append(point)
    rows: List[Dict[str, Any]] = []
    for eid in sorted(grouped):
        point = max(
            grouped[eid],
            key=lambda item: (str(item.get("as_of") or ""), str(item.get("tag_name") or "")),
        )
        display = str(point.get("tag_display_name") or point.get("tag_name") or "").strip()
        detail = lane_text(value_label(point.get("value")))
        if detail == display or detail == "（空）":
            detail = ""
        rows.append(
            {
                "entity_id": eid,
                "entity_name": str(lookup.get(eid) or eid),
                "tag_label": display or detail,
                "value_label": display or detail,
                "value_detail": detail,
                "as_of": str(point.get("as_of") or ""),
            }
        )
    return rows


def build_intervals(points: List[Dict[str, Any]], horizon_end: str = "") -> List[Dict[str, Any]]:
    """变化日接成区间。纵轴是标签展示名；下一次任一标签的变化结束上一段。

    同一天的多个标签一起保留到下一次变化。取值相同且首尾相接的段合并。
    ``value_label`` 只给悬停，不进纵轴。
    """
    ordered = [point for point in points if str(point.get("as_of") or "").strip()]
    ordered.sort(key=lambda item: (str(item.get("as_of") or ""), str(item.get("tag_name") or "")))
    events: List[Tuple[str, List[Dict[str, Any]]]] = []
    for point in ordered:
        as_of = str(point.get("as_of") or "")
        if events and events[-1][0] == as_of:
            events[-1][1].append(point)
        else:
            events.append((as_of, [point]))

    intervals: List[Dict[str, Any]] = []
    open_rows: List[Dict[str, Any]] = []
    horizon = str(horizon_end or "").strip()

    def close_open(end: str) -> None:
        nonlocal open_rows
        for current in open_rows:
            _close_open(current, end)
            intervals.append(current)
        open_rows = []

    for as_of, group in events:
        if open_rows:
            close_open(as_of)
        for row in group:
            display = str(row.get("tag_display_name") or row.get("tag_name") or "").strip()
            label = lane_text(value_label(row.get("value")))
            explicit = explicit_span(row)
            if explicit is not None:
                done = _interval_row(row, display, label, explicit[0], explicit[1])
                done["_explicit"] = True
                intervals.append(done)
                continue
            open_rows.append(_interval_row(row, display, label, as_of, ""))
    if open_rows:
        end = horizon if horizon > str(open_rows[0].get("start") or "") else ""
        if end:
            close_open(end)
        else:
            for current in open_rows:
                current["end"] = _next_day(str(current.get("start") or ""))
                intervals.append(current)
    return _merge_adjacent(intervals)


def build_snapshots(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """每个定义保留最新一点，并按值的形状收成可渲染块。"""
    latest: Dict[str, Dict[str, Any]] = {}
    for point in points:
        name = str(point.get("tag_name") or "")
        prev = latest.get(name)
        if prev is None or str(point.get("as_of") or "") >= str(prev.get("as_of") or ""):
            latest[name] = point
    snapshots: List[Dict[str, Any]] = []
    for name in sorted(latest):
        point = latest[name]
        shaped = shape_snapshot(point.get("value"))
        shaped["tag_name"] = name
        shaped["tag_display_name"] = str(point.get("tag_display_name") or name)
        shaped["as_of"] = str(point.get("as_of") or "")
        snapshots.append(shaped)
    return snapshots


def shape_snapshot(value: Any) -> Dict[str, Any]:
    """标量 → 卡片；类别字典 → 表；其余对象 → 字段表或文本。"""
    if is_scalar(value) or value is None:
        return {"kind": "scalar", "scalar": "" if value is None else lane_text(value_label(value))}
    if isinstance(value, dict):
        categories = category_rows(value)
        if categories is not None:
            return {"kind": "categories", "categories": categories}
        if value and all(is_scalar(item) or item is None for item in value.values()):
            return {
                "kind": "fields",
                "fields": [
                    {"name": str(key), "value": "" if item is None else lane_text(value_label(item))}
                    for key, item in value.items()
                ],
            }
        return {
            "kind": "object",
            "text": json.dumps(value, ensure_ascii=False, indent=2),
        }
    return {
        "kind": "object",
        "text": json.dumps(value, ensure_ascii=False, indent=2),
    }


def category_rows(value: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    mapping = category_map(value)
    if mapping is None:
        return None
    rows: List[Dict[str, Any]] = []
    for name, bucket in mapping.items():
        count = bucket.get("count")
        try:
            count_num = int(count) if count is not None and count != "" else None
        except (TypeError, ValueError):
            count_num = None
        samples = bucket.get("sample_ids") or bucket.get("samples") or bucket.get("ids") or []
        if not isinstance(samples, list):
            samples = []
        detail = _category_detail(bucket)
        rows.append(
            {
                "name": str(name),
                "count": count_num,
                "detail": detail,
                "samples": "、".join(str(item) for item in samples[:8]),
            }
        )
    rows.sort(key=lambda item: (-(item["count"] if item["count"] is not None else -1), item["name"]))
    return rows


def category_map(value: Any) -> Optional[Dict[str, Dict[str, Any]]]:
    if not isinstance(value, dict):
        return None
    direct = _as_category_map(value)
    if direct is not None:
        return direct
    best: Optional[Dict[str, Dict[str, Any]]] = None
    for nested in value.values():
        found = _as_category_map(nested)
        if found is not None and (best is None or len(found) > len(best)):
            best = found
    return best


def is_scalar(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    return isinstance(value, (int, float, str))


def value_label(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value).strip()
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(text) > 48:
        return text[:45] + "..."
    return text


def lane_text(label: str) -> str:
    text = str(label or "").strip()
    return text or "（空）"


def explicit_span(row: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    start = str(row.get("start_date") or "").strip()
    end = str(row.get("end_date") or "").strip()
    if start and end and end > start:
        return start, end
    return None


def _interval_row(
    row: Dict[str, Any],
    display: str,
    label: str,
    start: str,
    end: str,
) -> Dict[str, Any]:
    lane = display or str(row.get("tag_name") or "") or label
    return {
        "lane": lane,
        "value_label": label,
        "tag_name": str(row.get("tag_name") or ""),
        "tag_display_name": display,
        "start": start,
        "end": end,
    }


def _merge_adjacent(intervals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """同一标签、同一取值、首尾相接的段合成一根。显式区间不并进去。"""
    merged: List[Dict[str, Any]] = []
    for item in intervals:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and not prev.get("_explicit")
            and not item.get("_explicit")
            and prev.get("lane") == item.get("lane")
            and prev.get("value_label") == item.get("value_label")
            and prev.get("end") == item.get("start")
        ):
            prev["end"] = item.get("end")
            continue
        merged.append(item)
    for item in merged:
        item.pop("_explicit", None)
    return merged


def _close_open(current: Dict[str, Any], end: str) -> None:
    start = str(current.get("start") or "")
    current["end"] = end if end > start else _next_day(start)


def _as_category_map(candidate: Any) -> Optional[Dict[str, Dict[str, Any]]]:
    if not isinstance(candidate, dict) or not candidate:
        return None
    values = list(candidate.values())
    if all(isinstance(item, dict) for item in values) and any("count" in item for item in values):
        return candidate
    if all(isinstance(item, list) for item in values):
        return {
            str(key): {"count": len(item), "sample_ids": list(item[:8])}
            for key, item in candidate.items()
        }
    return None


def _category_detail(bucket: Dict[str, Any]) -> str:
    parts: List[str] = []
    provinces = bucket.get("provinces")
    if isinstance(provinces, list) and provinces:
        parts.append("、".join(str(item) for item in provinces))
    skip = {"count", "provinces", "sample_ids", "samples", "ids"}
    for key, item in bucket.items():
        if key in skip or not is_scalar(item):
            continue
        parts.append(f"{key}: {lane_text(value_label(item))}")
    return "；".join(parts)


def _yyyymmdd(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        return TagDataService._normalize_date_to_yyyymmdd(value)
    except Exception:
        text = str(value).strip().replace("-", "")
        if len(text) >= 8 and text[:8].isdigit():
            return text[:8]
        return None


def _next_day(yyyymmdd: str) -> str:
    try:
        day = datetime.strptime(str(yyyymmdd), "%Y%m%d") + timedelta(days=1)
    except ValueError:
        return str(yyyymmdd)
    return day.strftime("%Y%m%d")


__all__ = [
    "TagVisualization",
    "build_entity_rows",
    "build_intervals",
    "build_snapshots",
    "decode_value",
    "normalize_point",
    "shape_snapshot",
]
