"""
DuckdbTableOperator — DuckDB 单表 CRUD（写经 WritePipeline，读直连 connector）。
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.infra.db.core.engines.abc.table_abc import DbTableAbc
from core.infra.db.core.engines.duckdb.write_pipeline import _WriteJob
from core.infra.db.core.engines.shared.cursor import DatabaseCursor
from core.infra.db.core.engines.shared.dialect import quote_identifier_for_dialect
from core.infra.db.core.engines.shared import row_sql
from core.infra.db.core.table_queriers.services.batch_operation import BatchOperation

if TYPE_CHECKING:
    from core.infra.db.core.engines.duckdb.engine import DuckdbEngine

logger = logging.getLogger(__name__)


class DuckdbTableOperator(DbTableAbc):
    def __init__(self, engine: "DuckdbEngine", table_name: str) -> None:
        self._engine = engine
        self._table_name = str(table_name)
        self._domain = engine.resolve_domain(self._table_name)

    @property
    def table_name(self) -> str:
        return self._table_name

    @property
    def _domain_conn(self):
        return self._engine.connector.connection_for_domain(self._domain)

    def _sql_table(self) -> str:
        return quote_identifier_for_dialect("duckdb", self.table_name)

    def _insert_batch_size(self) -> int:
        return self._engine.meta.batch_write.insert_batch_size

    @contextmanager
    def _cursor(self):
        cursor = DatabaseCursor(self._domain_conn)
        try:
            yield cursor
        finally:
            cursor.close()

    def load(
        self,
        condition: str = "1=1",
        params: tuple = (),
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        table = self._sql_table()
        query = f"SELECT * FROM {table} WHERE {condition}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit is not None:
            query += f" LIMIT {limit}"
        if offset is not None:
            query += f" OFFSET {offset}"
        try:
            return self.query(query, params)
        except Exception as e:
            logger.error("Failed to load from %s: %s", self.table_name, e)
            return []

    def query(self, sql: str, params: Any = None) -> List[Dict[str, Any]]:
        return self._domain_conn.execute_query(sql, params)

    def execute_write(self, sql: str, params: Any = None) -> int:
        return self._domain_conn.execute_write(sql, params)

    def insert(
        self,
        rows: List[Dict[str, Any]],
        unique_keys: Optional[List[str]] = None,
    ) -> int:
        if not rows:
            return 0
        job = _WriteJob(
            table_name=self.table_name,
            op="insert",
            rows=rows,
            unique_keys=unique_keys,
            result_holder=[],
        )
        return self._engine._pipeline_for_domain(self._domain).submit(job, wait=True)

    def upsert(self, rows: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        if not rows:
            return 0
        job = _WriteJob(
            table_name=self.table_name,
            op="upsert",
            rows=rows,
            unique_keys=unique_keys,
            result_holder=[],
        )
        return self._engine._pipeline_for_domain(self._domain).submit(job, wait=True)

    def delete(
        self,
        condition: str,
        params: tuple = (),
        limit: Optional[int] = None,
    ) -> int:
        job = _WriteJob(
            table_name=self.table_name,
            op="delete",
            condition=condition,
            params=params,
            limit=limit,
            result_holder=[],
        )
        return self._engine._pipeline_for_domain(self._domain).submit(job, wait=True)

    def _insert_sync(
        self,
        rows: List[Dict[str, Any]],
        unique_keys: Optional[List[str]],
    ) -> int:
        if not rows:
            return 0
        try:
            if unique_keys:
                columns, values, update_clause = row_sql.to_upsert_params(rows, unique_keys)
            else:
                columns, _ = row_sql.to_columns_and_values(rows)
                values = row_sql.rows_to_value_tuples(rows, columns)
                update_clause = None
            if not columns:
                return 0
            with self._cursor() as cursor:
                return BatchOperation.execute_batch_insert(
                    executor=cursor,
                    table_name=self._sql_table(),
                    columns=columns,
                    values=values,
                    batch_size=self._insert_batch_size(),
                    database_type="duckdb",
                    unique_keys=unique_keys if unique_keys else None,
                    update_clause=update_clause if unique_keys else None,
                )
        except Exception as e:
            logger.error("Failed to insert into %s: %s", self.table_name, e)
            return 0

    def _delete_sync(
        self,
        condition: str,
        params: tuple,
        limit: Optional[int],
    ) -> int:
        table = self._sql_table()
        query = f"DELETE FROM {table} WHERE {condition}"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return self._domain_conn.execute_write(query, params)
            except Exception as e:
                logger.error(
                    "Failed to delete from %s (attempt %s/%s): %s",
                    self.table_name,
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt == max_retries - 1:
                    return 0
                time.sleep(0.1 * (2 ** attempt))
        return 0

    def count(self, condition: str = "1=1", params: tuple = ()) -> int:
        try:
            table = self._sql_table()
            query = f"SELECT COUNT(*) AS cnt FROM {table} WHERE {condition}"
            rows = self.query(query, params)
            if not rows:
                return 0
            row = rows[0]
            n = row.get("cnt") if "cnt" in row else row.get("count", 0)
            return int(n) if n is not None else 0
        except Exception as e:
            logger.error("Failed to count %s: %s", self.table_name, e)
            return 0

    def load_schema(self) -> Dict[str, Any]:
        schema = self._engine.schema_manager.get_table_schema(self.table_name)
        if not schema:
            raise ValueError(f"Schema not found for table: {self.table_name}")
        return schema

    def clear_table(self) -> int:
        return self.delete("1=1", ())
