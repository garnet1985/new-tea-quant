"""BatchOperation 写入格式化与读出口标量规范对称性。"""
from __future__ import annotations

from decimal import Decimal

import numpy as np

from core.infra.db.core.table_queriers.services.batch_operation import BatchOperation


def test_format_value_decimal_as_numeric_literal():
    assert BatchOperation.format_value_for_sql(Decimal("1.2300")) == "1.23"


def test_format_value_numpy_scalar():
    assert BatchOperation.format_value_for_sql(np.int64(9)) == "9"
    assert BatchOperation.format_value_for_sql(np.float64(1.5)) == "1.5"


def test_format_value_bool_before_int():
    assert BatchOperation.format_value_for_sql(True) == "TRUE"
    assert BatchOperation.format_value_for_sql(False) == "FALSE"
