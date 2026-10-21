"""ListService.filter_ids：多维度 include/exclude。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.modules.data_manager.core.data_services.stock.sub_services.list_service import (
    ListService,
)

pytestmark = pytest.mark.force_run


def _svc_with_rows(by_query: dict[str, list[dict]]) -> ListService:
    """by_query key = (dim, value) or ('all',) / ('list_status', frozenset)."""
    dm = MagicMock()
    dm.get_table.return_value = MagicMock()
    svc = ListService(dm)

    def _load(**kwargs):
        if "list_status" in kwargs and kwargs["list_status"] is not None:
            statuses = kwargs["list_status"]
            if isinstance(statuses, str):
                wanted = {statuses}
            else:
                wanted = {str(s) for s in statuses}
            out: list[dict] = []
            for status in wanted:
                out.extend(by_query.get(("list_status", status), []))
            return out
        for dim in ("industry", "board", "market", "area"):
            if kwargs.get(dim) is not None:
                return list(by_query.get((dim, kwargs[dim]), []))
        return list(by_query.get(("all",), []))

    svc.load = MagicMock(side_effect=lambda **kw: _load(**kw))  # type: ignore[method-assign]
    svc.load_all = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda order_by="id": list(by_query.get(("all",), []))
    )
    return svc


def test_filter_ids_include_and_across_dims() -> None:
    svc = _svc_with_rows(
        {
            ("all",): [
                {"id": "000001.SZ"},
                {"id": "600000.SH"},
                {"id": "000002.SZ"},
            ],
            ("market", "SSE"): [{"id": "600000.SH"}],
            ("market", "SZSE"): [{"id": "000001.SZ"}, {"id": "000002.SZ"}],
            ("list_status", "L"): [
                {"id": "000001.SZ"},
                {"id": "600000.SH"},
            ],
        }
    )
    out = svc.filter_ids(
        include={"market": ["SSE", "SZSE"], "list_status": ["L"]},
    )
    assert out == ["000001.SZ", "600000.SH"]


def test_filter_ids_exclude_then_universe() -> None:
    svc = _svc_with_rows(
        {
            ("industry", "银行"): [{"id": "600000.SH"}],
        }
    )
    out = svc.filter_ids(
        exclude={"industry": ["银行"]},
        universe=["000001.SZ", "600000.SH", "000002.SZ"],
    )
    assert out == ["000001.SZ", "000002.SZ"]


def test_filter_ids_empty_when_include_misses() -> None:
    svc = _svc_with_rows({("market", "BSE"): []})
    assert svc.filter_ids(include={"market": ["BSE"]}, universe=["000001.SZ"]) == []


def test_filter_ids_rejects_unknown_dim() -> None:
    svc = _svc_with_rows({})
    with pytest.raises(ValueError, match="未知维度"):
        svc.filter_ids(include={"sector": ["x"]})
