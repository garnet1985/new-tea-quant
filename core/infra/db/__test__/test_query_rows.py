"""query_rows — 读出口标量规范化单元测试。"""
from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest

from core.infra.db.engines._shared.query_rows import (
    fetch_result_to_normalized_rows,
    fetch_result_to_rows,
    normalize_cell_value,
    normalize_query_rows,
    tuples_to_dicts,
)


def test_decimal_to_float():
    assert normalize_cell_value(Decimal("1.2345")) == pytest.approx(1.2345)
    assert isinstance(normalize_cell_value(Decimal("1.2345")), float)


def test_none_and_nan():
    assert normalize_cell_value(None) is None
    assert normalize_cell_value(float("nan")) is None


def test_numpy_scalars():
    assert normalize_cell_value(np.int64(7)) == 7
    assert isinstance(normalize_cell_value(np.int64(7)), int)
    assert normalize_cell_value(np.float64(3.5)) == pytest.approx(3.5)
    assert isinstance(normalize_cell_value(np.float64(3.5)), float)
    assert normalize_cell_value(np.bool_(True)) is True


def test_normalize_query_rows():
    rows = normalize_query_rows(
        [{"factor": Decimal("2.5000"), "id": np.int64(1), "name": "x"}]
    )
    assert rows[0]["factor"] == pytest.approx(2.5)
    assert rows[0]["id"] == 1
    assert rows[0]["name"] == "x"


def test_tuples_to_dicts():
    out = tuples_to_dicts(["a", "b"], [(1, Decimal("0.1"))])
    assert out == [{"a": 1, "b": Decimal("0.1")}]


def test_fetch_result_to_rows_duckdb_connection_style():
    duckdb = pytest.importorskip("duckdb")
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE t (id INTEGER, factor DECIMAL(12,4))")
    conn.execute("INSERT INTO t VALUES (1, 1.2345)")
    rel = conn.execute("SELECT * FROM t")
    rows = fetch_result_to_rows(rel)
    assert rows == [{"id": 1, "factor": Decimal("1.2345")}]
    rel2 = conn.execute("SELECT * FROM t")
    norm = fetch_result_to_normalized_rows(rel2)
    assert norm == [{"id": 1, "factor": pytest.approx(1.2345)}]
    assert isinstance(norm[0]["factor"], float)
    assert isinstance(norm[0]["id"], int)
    conn.close()


def test_fetch_result_to_rows_duckdb_relation_style():
    duckdb = pytest.importorskip("duckdb")
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE t (n INTEGER)")
    conn.execute("INSERT INTO t VALUES (42)")
    rel = conn.sql("SELECT n FROM t")
    rows = fetch_result_to_normalized_rows(rel)
    assert rows == [{"n": 42}]
    conn.close()
