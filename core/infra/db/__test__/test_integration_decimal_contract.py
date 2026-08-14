"""DECIMAL 出入库契约：应用层只见 float，责任在 infra/db。"""
from __future__ import annotations

from decimal import Decimal

import pytest

from core.infra.db.core.engines.shared import row_sql
from core.infra.db.core.engines.duckdb.connector import DuckdbDomainConnection
from core.infra.db.core.table_queriers.services.batch_operation import BatchOperation


class TestWriteInlet:
    def test_rows_to_value_tuples_converts_decimal(self):
        tuples = row_sql.rows_to_value_tuples(
            [{"id": 1, "factor": Decimal("1.2345")}],
            ["id", "factor"],
        )
        assert tuples == [(1, 1.2345)]
        assert isinstance(tuples[0][1], float)

    def test_to_upsert_params_converts_decimal(self):
        _cols, values, _clause = row_sql.to_upsert_params(
            [{"id": "x", "event_date": "20240101", "factor": Decimal("2.5")}],
            ["id", "event_date"],
        )
        assert values[0][2] == 2.5
        assert isinstance(values[0][2], float)

    def test_format_value_for_sql_after_normalize(self):
        sql = BatchOperation.format_value_for_sql(Decimal("3.1400"))
        assert sql == "3.14"


class TestDuckDbReadWriteContract:
    def test_decimal_column_round_trip_is_float(self, tmp_path):
        db_path = tmp_path / "decimal.duckdb"
        conn = DuckdbDomainConnection({"db_path": str(db_path)}, domain="data")
        conn.connect()
        conn.execute_write(
            "CREATE TABLE ev (id INTEGER, factor DECIMAL(12,4))"
        )
        # 写入口：即使传入 Decimal 也规范为 float 再落库
        conn.execute_write("INSERT INTO ev VALUES (?, ?)", (1, Decimal("9.8765")))

        rows = conn.execute_query("SELECT id, factor FROM ev")
        assert len(rows) == 1
        assert rows[0]["id"] == 1
        assert rows[0]["factor"] == pytest.approx(9.8765)
        assert isinstance(rows[0]["factor"], float)
        assert not any(isinstance(v, Decimal) for v in rows[0].values())
        conn.close()
