from __future__ import annotations

from typing import Any, List, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager
from core.utils.date.date_utils import DateUtils


def _extract_stock_id(params: Mapping[str, Any], context: Optional[Mapping[str, Any]]) -> str:
    candidate = (
        params.get("stock_id")
        or params.get("id")
        or (context or {}).get("stock_id")
        or (context or {}).get("id")
        or (context or {}).get("entity_id")
    )
    if not candidate:
        raise ValueError("加载 stock.kline.daily 失败：缺少 stock_id（可放在 params/context）")
    return str(candidate)


def _drop_boundary_rows(
    rows: List[Mapping[str, Any]],
    *,
    start: Optional[str],
    end: Optional[str],
    include_boundary: bool,
) -> List[Mapping[str, Any]]:
    if include_boundary:
        return rows

    out: List[Mapping[str, Any]] = []
    for row in rows:
        row_date = DateUtils.normalize_str(row.get("date")) if row.get("date") else None
        if row_date is None:
            out.append(row)
            continue
        if start is not None and row_date == start:
            continue
        if end is not None and row_date == end:
            continue
        out.append(row)
    return out


def _load_by_adjust(
    *,
    kline_service: Any,
    stock_id: str,
    term: str,
    start: Optional[str],
    end: Optional[str],
    adjust: str,
) -> List[Mapping[str, Any]]:
    if adjust == "qfq":
        return kline_service.load_qfq(stock_id=stock_id, term=term, start_date=start, end_date=end)
    if adjust in ("nfq", "none"):
        return kline_service.load_raw(stock_id=stock_id, term=term, start_date=start, end_date=end)
    raise ValueError(f"加载 stock.kline.daily 失败：不支持 adjust={adjust!r}，仅支持 qfq/nfq/none")


class StockKlineLoader(BaseLoader):
    """Unified loader for stock kline (qfq/nfq)."""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        data_mgr = DataManager()
        kline_service = data_mgr.stock.kline

        stock_id = _extract_stock_id(params, context)
        term = str(params.get("term", "daily"))
        adjust = str(params.get("adjust", "qfq")).lower()

        start = DateUtils.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = DateUtils.normalize_str(params.get("end")) if params.get("end") is not None else None
        amount = params.get("amount")
        direction = int(params.get("direction", -1))
        include_boundary = bool(params.get("include_boundary", True))

        if amount is not None:
            if not isinstance(amount, int):
                raise TypeError("加载 stock.kline.daily 失败：amount 必须是 int")
            if amount < 1:
                raise ValueError("加载 stock.kline.daily 失败：amount 必须 >= 1")
        if direction not in (-1, 1):
            raise ValueError("加载 stock.kline.daily 失败：direction 只能是 -1 或 1")
        if start is None and end is not None:
            raise ValueError("加载 stock.kline.daily 失败：仅传 end 无效，需同时传 start")
        if end is not None and amount is not None:
            raise ValueError("加载 stock.kline.daily 失败：end 与 amount 不能同时传入")

        # all
        if start is None and end is None and amount is None:
            return _load_by_adjust(
                kline_service=kline_service,
                stock_id=stock_id,
                term=term,
                start=None,
                end=None,
                adjust=adjust,
            )

        # range
        if start is not None and end is not None:
            left, right = (start, end) if start <= end else (end, start)
            rows = _load_by_adjust(
                kline_service=kline_service,
                stock_id=stock_id,
                term=term,
                start=left,
                end=right,
                adjust=adjust,
            )
            return _drop_boundary_rows(rows, start=left, end=right, include_boundary=include_boundary)

        # point / lookback / lookforward
        if start is None:
            raise ValueError("加载 stock.kline.daily 失败：仅传 amount/direction 无效，需同时传 start")

        normalized_amount = amount if amount is not None else 1
        if direction == -1:
            rows = _load_by_adjust(
                kline_service=kline_service,
                stock_id=stock_id,
                term=term,
                start=None,
                end=start,
                adjust=adjust,
            )
            rows = _drop_boundary_rows(rows, start=None, end=start, include_boundary=include_boundary)
            return rows[-normalized_amount:]

        rows = _load_by_adjust(
            kline_service=kline_service,
            stock_id=stock_id,
            term=term,
            start=start,
            end=None,
            adjust=adjust,
        )
        rows = _drop_boundary_rows(rows, start=start, end=None, include_boundary=include_boundary)
        return rows[:normalized_amount]
