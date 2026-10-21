"""SeriesRelation settings 校验与规范化。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from core.modules.series_relation.core.constants import (
    FILL_MODES,
    MAX_SERIES,
    NORMALIZE_MODES,
)

DeclarationLookup = Callable[[str], Optional[Mapping[str, Any]]]


def validate_settings(
    raw: Any,
    *,
    declaration_lookup: Optional[DeclarationLookup] = None,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """校验并返回规范化 settings；失败时 ``(None, errors)``。"""
    errors: List[str] = []
    if not isinstance(raw, Mapping):
        return None, ["settings 必须是 dict"]

    meta_raw = raw.get("meta")
    if not isinstance(meta_raw, Mapping):
        errors.append("缺少 meta 或 meta 不是 dict")
        meta: Dict[str, Any] = {}
    else:
        meta = dict(meta_raw)
    key = str(meta.get("key") or "").strip()
    if not key:
        errors.append("缺少 meta.key")

    series_raw = raw.get("series")
    if not isinstance(series_raw, list) or not series_raw:
        errors.append("series 必须是非空 list")
        series_raw = []
    if len(series_raw) > MAX_SERIES:
        errors.append(f"series 最多 {MAX_SERIES} 条（模块常量 MAX_SERIES）")

    normalized_series: List[Dict[str, Any]] = []
    seen: set = set()
    for index, item in enumerate(series_raw):
        if not isinstance(item, Mapping):
            errors.append(f"series[{index}] 必须是 dict")
            continue
        data_key = str(item.get("data_key") or "").strip()
        field = str(item.get("field") or "").strip()
        entity_id = str(item.get("entity_id") or "").strip()
        label = str(item.get("label") or "").strip()
        if not data_key:
            errors.append(f"series[{index}] 缺少 data_key")
        if not field:
            errors.append(f"series[{index}] 缺少 field")

        scope = ""
        if data_key and declaration_lookup is not None:
            decl = declaration_lookup(data_key)
            if decl is None:
                errors.append(f"series[{index}] 未知 data_key: {data_key}")
            else:
                meta_decl = decl.get("meta") if isinstance(decl.get("meta"), Mapping) else {}
                ctype = str(meta_decl.get("type") or "").strip()
                scope = str(meta_decl.get("scope") or "").strip()
                if ctype != "time_series":
                    errors.append(
                        f"series[{index}] data_key={data_key} 不是 time_series（type={ctype or '-'}）"
                    )
                if scope == "per_entity" and not entity_id:
                    errors.append(
                        f"series[{index}] per_entity 必须提供 entity_id"
                    )
                if scope == "global" and entity_id:
                    # 忽略多余 entity_id，不报错
                    entity_id = ""

        dedupe = (data_key, entity_id, field)
        if data_key and field and dedupe in seen:
            errors.append(
                f"series[{index}] 与已有项重复: {data_key}/{entity_id or '-'}#{field}"
            )
        seen.add(dedupe)

        if not label and data_key and field:
            label = f"{data_key}.{field}" if not entity_id else f"{entity_id}.{field}"

        normalized_series.append(
            {
                "data_key": data_key,
                "field": field,
                "entity_id": entity_id,
                "label": label,
                "scope": scope,
            }
        )

    range_raw = raw.get("range") if isinstance(raw.get("range"), Mapping) else {}
    start_date = str(range_raw.get("start_date") or "").strip()
    end_date = str(range_raw.get("end_date") or "").strip()
    if start_date and end_date and start_date > end_date:
        errors.append("range.start_date 不能晚于 end_date")

    normalize = str(raw.get("normalize") or "zscore").strip() or "zscore"
    if normalize not in NORMALIZE_MODES:
        errors.append(f"normalize 非法: {normalize}（允许 {sorted(NORMALIZE_MODES)}）")

    fill = str(raw.get("fill") or "none").strip() or "none"
    if fill not in FILL_MODES:
        errors.append(f"fill 非法: {fill}（允许 {sorted(FILL_MODES)}）")

    analyze = bool(raw.get("analyze", True))

    if "max_series" in raw:
        errors.append("max_series 不进用户配置（由模块常量 MAX_SERIES 限制）")

    if errors:
        return None, errors

    return {
        "meta": {
            "key": key,
            "display_name": str(meta.get("display_name") or "").strip() or key,
        },
        "series": normalized_series,
        "range": {"start_date": start_date, "end_date": end_date},
        "normalize": normalize,
        "fill": fill,
        "analyze": analyze,
    }, []


__all__ = ["validate_settings", "DeclarationLookup"]
