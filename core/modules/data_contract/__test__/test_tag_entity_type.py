"""Tag entity_type 与 DataKey 映射。"""

from __future__ import annotations

import pytest

from core.modules.data_contract.contracts import DataKey
from core.modules.data_contract.core.registry.tag_entity_type import resolve_tag_entity_type


@pytest.mark.parametrize(
    ("data_id", "expected"),
    [
        (DataKey.STOCK_KLINE_DAILY, "stock_kline_daily"),
        (DataKey.STOCK_KLINE_WEEKLY, "stock_kline_weekly"),
        (DataKey.STOCK_CORPORATE_FINANCE, "corporate_finance"),
        (DataKey.TAG, "tag_scenario"),
        (DataKey.INDEX_KLINE_DAILY, "index_kline_daily"),
    ],
)
def test_resolve_tag_entity_type(data_id: DataKey, expected: str) -> None:
    assert resolve_tag_entity_type(data_id) == expected


def test_resolve_tag_entity_type_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="无法推导"):
        resolve_tag_entity_type(DataKey.MACRO_GDP)
