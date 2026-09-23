"""归档 CSV 直接装入，不经过 Python 字典。"""
from contextlib import contextmanager
from unittest.mock import Mock, patch

import duckdb

from core.infra.db.core.engines.duckdb.connector import _DuckDBTransactionCursor
from core.infra.db.core.table_queriers.csv_bulk_import import schema_has_json
from core.infra.db.core.table_queriers.db_base_model import DbBaseModel
from core.infra.utils import Utils


_SCHEMA = {
    "name": "demo",
    "primaryKey": "id",
    "fields": [
        {"name": "id", "type": "varchar"},
        {"name": "close", "type": "float"},
        {"name": "is_open", "type": "tinyint"},
        {"name": "last_update", "type": "datetime"},
        {"name": "note", "type": "varchar"},
    ],
}


def _model(con):
    db = Mock()
    db.is_duckdb = True
    db.config = {"database_type": "duckdb"}
    db.uses_engine_path = False
    db._initialized = False

    @contextmanager
    def tx():
        yield _DuckDBTransactionCursor(con)

    with patch.object(DbBaseModel, "load_schema", return_value=_SCHEMA):
        model = DbBaseModel("demo", db=db)
    model._table_transaction = tx
    return model


def test_schema_has_json_detects_json_columns():
    assert schema_has_json({"fields": [{"name": "payload", "type": "json"}]})
    assert not schema_has_json(_SCHEMA)


def test_import_data_reads_csv_in_duckdb(tmp_path):
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE demo (id VARCHAR, close DOUBLE, is_open INTEGER, "
        "last_update TIMESTAMP, note VARCHAR)"
    )
    archive = Utils.io.write_archive(
        tmp_path,
        "demo",
        {
            "demo.csv": (
                b"id,close,is_open,last_update,note\n"
                b"a,1.5,1,2023-01-01 12:00:00,\n"
                b"b,,0,,x\n"
            )
        },
        format="tar.gz",
    )
    _model(con).import_data([archive])
    rows = con.execute(
        "SELECT id, close, is_open, last_update, note FROM demo ORDER BY id"
    ).fetchall()
    assert rows[0][0] == "a"
    assert rows[0][1] == 1.5
    assert rows[0][2] == 1
    assert str(rows[0][3]).startswith("2023-01-01")
    assert rows[0][4] == ""
    assert rows[1] == ("b", None, 0, None, "x")


def test_postgres_select_expr_casts_timestamp_and_int():
    from core.infra.db.core.table_queriers.csv_bulk_import import _select_expr

    assert _select_expr('"last_update"', "datetime", "postgresql") == (
        'CAST(NULLIF("last_update", \'\') AS TIMESTAMP)'
    )
    assert _select_expr('"is_open"', "tinyint", "postgresql") == (
        'CAST(NULLIF("is_open", \'\') AS SMALLINT)'
    )
    assert _select_expr('"note"', "varchar", "postgresql") == '"note"'


def test_json_column_keeps_row_insert_path():
    con = duckdb.connect()
    model = _model(con)
    model.schema = {
        "fields": [
            {"name": "id", "type": "varchar"},
            {"name": "payload", "type": "json"},
        ]
    }
    model._import_data_file_loop_rows = lambda *args, **kwargs: 7
    loaded = model._import_data_file_loop(
        None,
        "demo",
        [],
        None,
        pg_execute_values=False,
    )
    assert loaded == 7


def test_mysql_copy_uses_load_data_local_infile(tmp_path):
    from core.infra.db.core.table_queriers.csv_bulk_import import copy_csv_file

    csv_path = tmp_path / "demo.csv"
    csv_path.write_text("id,close,note\na,1.5,\nb,,x\n", encoding="utf-8")
    executed: list[str] = []
    counts = iter([0, 2])

    class FakeCursor:
        def execute(self, sql, params=None):
            executed.append(sql)
            if sql.startswith("SELECT COUNT(*)"):
                self._row = {"cnt": next(counts)}

        def fetchone(self):
            return getattr(self, "_row", None)

    def quote(name: str) -> str:
        return f"`{name}`"

    n = copy_csv_file(
        FakeCursor(),
        database_type="mysql",
        target_sql="demo",
        csv_path=csv_path,
        type_by_name={"id": "varchar", "close": "float", "note": "varchar"},
        quote=quote,
    )
    assert n == 2
    blob = "\n".join(executed)
    assert "LOAD DATA LOCAL INFILE" in blob
    assert "CREATE TEMPORARY TABLE" in blob
    assert "INSERT INTO demo" in blob
    assert "CAST(NULLIF(`close`, '') AS DOUBLE)" in blob
