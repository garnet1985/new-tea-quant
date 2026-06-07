"""DuckDB 连接在 BFF 多线程下的查询串行化。"""
from __future__ import annotations

import threading

import duckdb

from core.infra.db.engines.duckdb.connector import DuckdbDomainConnection


def test_concurrent_execute_query_on_one_connection(tmp_path):
    db_path = tmp_path / "strategy.duckdb"
    duckdb.connect(str(db_path)).execute(
        'CREATE TABLE t (id INTEGER, name VARCHAR); '
        "INSERT INTO t VALUES (1, 'a'), (2, 'b')"
    ).close()

    conn = DuckdbDomainConnection({"db_path": str(db_path)}, domain="strategy")
    conn.connect()
    errors: list[BaseException] = []
    barrier = threading.Barrier(16)

    def worker(i: int):
        try:
            barrier.wait(timeout=5)
            rows = conn.execute_query(
                "SELECT * FROM t WHERE id >= ? ORDER BY id LIMIT 10",
                (1 + (i % 2),),
            )
            assert rows
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors
    conn.close()
