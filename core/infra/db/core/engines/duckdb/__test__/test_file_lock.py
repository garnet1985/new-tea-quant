"""DuckdbFileLock：分类与 release 保护规则。"""

from __future__ import annotations

from core.infra.db.core.engines.duckdb.file_lock import DuckdbFileLock


def test_annotate_kinds() -> None:
    self_pid = 111
    rows = [
        {"pid": 111, "command": "python -c pass"},
        {"pid": 222, "command": "/usr/libexec/fileproviderd"},
        {"pid": 333, "command": "python launcher.py -d"},
        {"pid": 444, "command": "python -c from core.modules.data_manager import DataManager"},
    ]
    for row in rows:
        DuckdbFileLock._annotate(row, self_pid=self_pid)
    assert rows[0]["kind"] == "self"
    assert rows[1]["kind"] == "system"
    assert rows[2]["kind"] == "active_app"
    assert rows[3]["kind"] == "stale_candidate"


def test_release_without_kill_only_lists(monkeypatch) -> None:
    monkeypatch.setattr(
        DuckdbFileLock,
        "inspect",
        classmethod(
            lambda cls, db_dir=None: {
                "ok": True,
                "db_dir": "/tmp/db",
                "files": ["/tmp/db/data.duckdb"],
                "holders": [
                    {
                        "pid": 444,
                        "kind": "stale_candidate",
                        "command": "python -c x",
                        "killable": True,
                    }
                ],
                "blocked": True,
                "note": "n",
            }
        ),
    )
    out = DuckdbFileLock.release(kill=False)
    assert out["killed"] == []
    assert out["skipped"][0]["reason"].startswith("kill=false")
