"""DuckDB WAL 打开策略：只读连接不得删除 .wal。"""
import duckdb
import pytest

from core.infra.db.engines.duckdb.connector import DuckdbDomainConnection


def test_read_only_wal_replay_failure_does_not_delete_wal(tmp_path, monkeypatch):
    db_path = tmp_path / "test.duckdb"
    wal_path = tmp_path / "test.duckdb.wal"
    wal_path.write_text("fake-wal")
    deleted = []

    class FakeExc(Exception):
        pass

    def fake_connect(path, read_only=False):
        raise FakeExc("Failure while replaying WAL file")

    monkeypatch.setattr(duckdb, "connect", fake_connect)
    monkeypatch.setattr(
        "pathlib.Path.unlink",
        lambda self, *a, **k: deleted.append(self),
    )

    adapter = DuckdbDomainConnection({"db_path": str(db_path), "read_only": True})
    with pytest.raises(RuntimeError, match="不要在写库进行中用只读连接"):
        adapter._open_connection(str(db_path), read_only=True)

    assert deleted == []
    assert wal_path.exists()
