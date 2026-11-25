"""SeriesRelation settings 校验与规范化。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from core.modules.series_relation.core.constants import (
    FILL_MODES,
    MAX_SERIES,
    NORMALIZE_MODES,
    SOURCE_DATA_KEY,
    SOURCE_STRATEGY_SIM,
    STRATEGY_SIM_LAYER_METRICS,
    TRANSFORM_MODES,
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
        source = _infer_source(item)
        if source == SOURCE_STRATEGY_SIM:
            row, row_errors = _normalize_strategy_sim(index, item, seen)
        else:
            row, row_errors = _normalize_data_key(
                index, item, seen, declaration_lookup=declaration_lookup
            )
        errors.extend(row_errors)
        if row is not None:
            normalized_series.append(row)

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


def _infer_source(item: Mapping[str, Any]) -> str:
    explicit = str(item.get("source") or "").strip()
    if explicit:
        return explicit
    if str(item.get("data_key") or "").strip():
        return SOURCE_DATA_KEY
    if (
        str(item.get("strategy_key") or item.get("strategy") or "").strip()
        or str(item.get("layer") or "").strip()
    ):
        return SOURCE_STRATEGY_SIM
    return SOURCE_DATA_KEY


def _strategy_ref(item: Mapping[str, Any]) -> str:
    """优先 ``strategy_key``（meta.key），``strategy`` 为别名（key 或相对路径均可）。"""
    return str(item.get("strategy_key") or item.get("strategy") or "").strip()


def _normalize_transform(
    index: int,
    item: Mapping[str, Any],
    *,
    default: str,
) -> Tuple[str, List[str]]:
    errors: List[str] = []
    raw = item.get("transform")
    if raw is None or str(raw).strip() == "":
        return default, errors
    transform = str(raw).strip()
    if transform not in TRANSFORM_MODES:
        errors.append(
            f"series[{index}] transform 非法: {transform}（允许 {sorted(TRANSFORM_MODES)}）"
        )
    return transform, errors


def _normalize_data_key(
    index: int,
    item: Mapping[str, Any],
    seen: set,
    *,
    declaration_lookup: Optional[DeclarationLookup],
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    errors: List[str] = []
    data_key = str(item.get("data_key") or "").strip()
    field = str(item.get("field") or "").strip()
    entity_id = str(item.get("entity_id") or "").strip()
    label = str(item.get("label") or "").strip()
    if not data_key:
        errors.append(f"series[{index}] 缺少 data_key（或改用 source=strategy_sim）")
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
                errors.append(f"series[{index}] per_entity 必须提供 entity_id")
            if scope == "global" and entity_id:
                entity_id = ""

    dedupe = ("data_key", data_key, entity_id, field)
    if data_key and field and dedupe in seen:
        errors.append(
            f"series[{index}] 与已有项重复: {data_key}/{entity_id or '-'}#{field}"
        )
    seen.add(dedupe)

    if not label and data_key and field:
        label = f"{data_key}.{field}" if not entity_id else f"{entity_id}.{field}"

    transform, t_errors = _normalize_transform(index, item, default="none")
    errors.extend(t_errors)

    if errors:
        return None, errors
    return {
        "source": SOURCE_DATA_KEY,
        "data_key": data_key,
        "field": field,
        "entity_id": entity_id,
        "label": label,
        "scope": scope,
        "transform": transform,
    }, []


def _normalize_strategy_sim(
    index: int,
    item: Mapping[str, Any],
    seen: set,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    errors: List[str] = []
    strategy_key = _strategy_ref(item)
    version = str(item.get("version") or "").strip() or "latest"
    layer = str(item.get("layer") or "").strip()
    metric = str(item.get("metric") or "").strip()
    entity_id = str(item.get("entity_id") or "").strip()
    label = str(item.get("label") or "").strip()

    if not strategy_key:
        errors.append(
            f"series[{index}] strategy_sim 缺少 strategy_key"
            f"（推荐填策略 meta.key；也可用相对路径，别名字段 strategy）"
        )
    if not layer:
        errors.append(f"series[{index}] strategy_sim 缺少 layer")
    if not metric:
        errors.append(f"series[{index}] strategy_sim 缺少 metric")
    if layer and metric and (layer, metric) not in STRATEGY_SIM_LAYER_METRICS:
        errors.append(
            f"series[{index}] 不支持 layer={layer!r} metric={metric!r}；"
            f"允许 {sorted(STRATEGY_SIM_LAYER_METRICS)}"
        )
    if layer == "portfolio" and metric == "equity" and entity_id:
        errors.append(
            f"series[{index}] portfolio.equity 不支持 entity_id；"
            f"单票请用 layer=price metric=cum_exit_roi"
        )

    dedupe = ("strategy_sim", strategy_key, version, layer, metric, entity_id)
    if strategy_key and layer and metric and dedupe in seen:
        errors.append(
            f"series[{index}] 与已有 strategy_sim 项重复: "
            f"{strategy_key}@{version}/{layer}.{metric}/{entity_id or '-'}"
        )
    seen.add(dedupe)

    if not label and strategy_key and layer and metric:
        base = f"{strategy_key}:{layer}.{metric}"
        label = f"{base}@{entity_id}" if entity_id else base

    transform, t_errors = _normalize_transform(index, item, default="returns")
    errors.extend(t_errors)

    if errors:
        return None, errors
    return {
        "source": SOURCE_STRATEGY_SIM,
        # 规范字段；strategy 同步保留，便于旧读写
        "strategy_key": strategy_key,
        "strategy": strategy_key,
        "version": version,
        "layer": layer,
        "metric": metric,
        "entity_id": entity_id,
        "label": label,
        "transform": transform,
        # 兼容 meta 展示字段
        "data_key": "",
        "field": metric,
        "scope": "strategy_sim",
    }, []


__all__ = ["validate_settings", "DeclarationLookup"]
