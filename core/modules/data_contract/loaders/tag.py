from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager
from core.utils.date.date_utils import DateUtils


def _has_scenario_input(params: Mapping[str, Any], context: Optional[Mapping[str, Any]]) -> bool:
    """是否提供了任一 scenario 相关入参（不含 DB 解析）。"""
    ctx = context or {}
    for key in ("tag_scenario", "scenario_name"):
        v = params.get(key) or ctx.get(key)
        if v is not None and str(v).strip() != "":
            return True
    if params.get("scenario_id") is not None or ctx.get("scenario_id") is not None:
        return True
    return False


def _extract_entity_id(params: Mapping[str, Any], context: Optional[Mapping[str, Any]]) -> str:
    candidate = (
        params.get("entity_id")
        or params.get("stock_id")
        or params.get("id")
        or (context or {}).get("entity_id")
        or (context or {}).get("stock_id")
        or (context or {}).get("id")
    )
    if not candidate:
        raise ValueError(
            "加载 tag 失败：缺少实体标识（请在 params 或 context 中提供 entity_id / stock_id / id）"
        )
    return str(candidate)


def _resolve_scenario_name(
    params: Mapping[str, Any],
    context: Optional[Mapping[str, Any]],
    *,
    tag_service: Any,
) -> str:
    """
    解析 scenario，用于 load_values_for_entity 的 scenario_name 参数。
    优先级：tag_scenario / scenario_name > scenario_id。
    """
    ctx = context or {}
    raw = (
        params.get("tag_scenario")
        or params.get("scenario_name")
        or ctx.get("tag_scenario")
        or ctx.get("scenario_name")
    )
    scenario_id = params.get("scenario_id") or ctx.get("scenario_id")

    if raw is not None and str(raw).strip() != "":
        raw_s = str(raw).strip()
        if raw_s.isdigit():
            row = next((x for x in (tag_service.list_scenarios() or []) if x.get("id") == int(raw_s)), None)
            if not row or not row.get("name"):
                raise ValueError(f"加载 tag 失败：未找到 scenario id={raw_s}")
            return str(row["name"])
        return raw_s

    if scenario_id is not None:
        row = next((x for x in (tag_service.list_scenarios() or []) if x.get("id") == int(scenario_id)), None)
        if not row or not row.get("name"):
            raise ValueError(f"加载 tag 失败：未找到 scenario_id={scenario_id!r}")
        return str(row["name"])

    raise ValueError(
        "加载 tag 失败：缺少 scenario 标识（请在 params 或 context 中提供 "
        "tag_scenario / scenario_name，或提供 scenario_id）"
    )


def _drop_boundary_rows(
    rows: List[Mapping[str, Any]],
    *,
    start: Optional[str],
    end: Optional[str],
    include_boundary: bool,
    time_field: str,
) -> List[Mapping[str, Any]]:
    if include_boundary:
        return rows

    out: List[Mapping[str, Any]] = []
    for row in rows:
        raw_d = row.get(time_field)
        row_date = DateUtils.normalize_str(raw_d) if raw_d is not None else None
        if row_date is None:
            out.append(row)
            continue
        if start is not None and row_date == start:
            continue
        if end is not None and row_date == end:
            continue
        out.append(row)
    return out


class TagLoader(BaseLoader):
    """
    统一 tag 数据 loader：DataKey 恒为 `tag`，通过 scenario 区分业务场景。

    约定：
    - 必须能解析出 scenario（tag_scenario / scenario_name 或 scenario_id）
    - 必须提供实体（entity_id / stock_id / id）
    - 时间窗口语义与 stock kline loader 对齐（start/end/amount/direction/include_boundary）
    """

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        entity_id = _extract_entity_id(params, context)
        if not _has_scenario_input(params, context):
            raise ValueError(
                "加载 tag 失败：缺少 scenario 标识（请在 params 或 context 中提供 "
                "tag_scenario / scenario_name，或提供 scenario_id）"
            )

        data_mgr = DataManager()
        tag_service = data_mgr.stock.tags

        entity_type = str(params.get("entity_type") or (context or {}).get("entity_type") or "stock")
        scenario_name = _resolve_scenario_name(params, context, tag_service=tag_service)

        time_field = "as_of_date"
        start = DateUtils.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = DateUtils.normalize_str(params.get("end")) if params.get("end") is not None else None
        amount = params.get("amount")
        direction = int(params.get("direction", -1))
        include_boundary = bool(params.get("include_boundary", True))

        if amount is not None:
            if not isinstance(amount, int):
                raise TypeError("加载 tag 失败：amount 必须是 int")
            if amount < 1:
                raise ValueError("加载 tag 失败：amount 必须 >= 1")
        if direction not in (-1, 1):
            raise ValueError("加载 tag 失败：direction 只能是 -1 或 1")
        if start is None and end is not None:
            raise ValueError("加载 tag 失败：仅传 end 无效，需同时传 start")
        if end is not None and amount is not None:
            raise ValueError("加载 tag 失败：end 与 amount 不能同时传入")

        def _fetch(q_start: str, q_end: str) -> List[Dict[str, Any]]:
            return tag_service.load_values_for_entity(
                entity_id=entity_id,
                scenario_name=scenario_name,
                start_date=q_start,
                end_date=q_end,
                entity_type=entity_type,
            )

        # all
        if start is None and end is None and amount is None:
            return _fetch(DateUtils.get_query_date_range_min(), DateUtils.QUERY_DATE_RANGE_MAX)

        # range
        if start is not None and end is not None:
            left, right = (start, end) if start <= end else (end, start)
            rows = _fetch(left, right)
            return _drop_boundary_rows(
                rows, start=left, end=right, include_boundary=include_boundary, time_field=time_field
            )

        if start is None:
            raise ValueError("加载 tag 失败：仅传 amount/direction 无效，需同时传 start")

        normalized_amount = amount if amount is not None else 1
        if direction == -1:
            rows = _fetch(DateUtils.get_query_date_range_min(), start)
            rows = _drop_boundary_rows(
                rows, start=None, end=start, include_boundary=include_boundary, time_field=time_field
            )
            return rows[-normalized_amount:]

        rows = _fetch(start, DateUtils.QUERY_DATE_RANGE_MAX)
        rows = _drop_boundary_rows(
            rows, start=start, end=None, include_boundary=include_boundary, time_field=time_field
        )
        return rows[:normalized_amount]
