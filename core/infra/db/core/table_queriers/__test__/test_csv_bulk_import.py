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
    con.execute("CREATE TABLE demo (id VARCHAR, close DOUBLE, note VARCHAR)")
    archive = Utils.io.write_archive(
        tmp_path,
        "demo",
        {"demo.csv": b"id,close,note\na,1.5,\nb,,x\n"},
        format="tar.gz",
    )
    _model(con).import_data([archive])
    rows = con.execute("SELECT id, close, note FROM demo ORDER BY id").fetchall()
    assert rows == [("a", 1.5, ""), ("b", None, "x")]


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
