"""运行状态文件：任务栏、失败摘要、保留正在跑的目录。"""
from __future__ import annotations

import json
import os

from core.modules.data_source.core.service.run_status import (
    RunStatus,
    ordered_source_keys,
    prune_runs,
)


class _Handler:
    def __init__(self, key: str) -> None:
        self._key = key
        self.context = {
            "config": None,
            "_bundle_error_count": 2,
            "_bundle_errors": ["job-1: 频率超限"],
        }
        self._last_run_timing = {"plan": 4, "execute": 2.2}

    def get_key(self) -> str:
        return self._key

    def renew_mode_label(self, *, force: bool = False) -> str:
        return "refresh" if force else "incremental"


def test_ordered_source_keys_respects_depends_on() -> None:
    enabled = {
        "cpi": {"depends_on": ["stock_list"]},
        "stock_list": {"depends_on": []},
    }
    assert ordered_source_keys(enabled) == ["stock_list", "cpi"]


def test_ordered_source_keys_runs_larger_weight_first() -> None:
    enabled = {
        "cpi": {"weight": 1},
        "gdp": {"weight": 10},
        "stock_list": {},
    }
    assert ordered_source_keys(enabled) == ["gdp", "cpi", "stock_list"]


def test_ordered_source_keys_stops_when_weight_reverses_dependency() -> None:
    import pytest

    enabled = {
        "stock_list": {"weight": 1},
        "stock_klines": {"weight": 10, "depends_on": ["stock_list"]},
    }
    with pytest.raises(ValueError, match="已停止"):
        ordered_source_keys(enabled)


def test_status_file_records_plan_and_bundle_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NTQ_RUN_DIR", str(tmp_path / "run-1"))
    monkeypatch.delenv("NTQ_RUNS_DIR", raising=False)
    handler = _Handler("cpi")
    status = RunStatus.open([handler])
    status.mark_running("cpi")
    status.mark_done(handler)
    payload = json.loads((tmp_path / "run-1" / "status.json").read_text(encoding="utf-8"))
    task = payload["tasks"][0]
    assert task["status"] == "done"
    assert task["table"] == ""
    assert task["mode"] == "incremental"
    assert task["plan_seconds"] == 4
    assert task["execute_seconds"] == 2.2
    assert task["total_seconds"] is not None
    assert task["total_seconds"] >= 0
    assert task["error"].startswith("失败 2 个任务")
    assert (tmp_path / "run-1" / "failures" / "cpi.log").is_file()
    assert (tmp_path / "run-1" / "tasks.json").is_file()


def test_progress_is_written_onto_the_running_task(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NTQ_RUN_DIR", str(tmp_path / "run-progress"))
    monkeypatch.delenv("NTQ_RUNS_DIR", raising=False)
    handler = _Handler("cpi")
    status = RunStatus.open([handler])
    status.mark_running("cpi")
    status.note_progress("cpi", done=1, total=4, saved=2, label="抓取 1/4，已写入 2 行")
    payload = json.loads((tmp_path / "run-progress" / "status.json").read_text(encoding="utf-8"))
    task = payload["tasks"][0]
    assert task["status"] == "running"
    assert task["progress_done"] == 1
    assert task["progress_total"] == 4
    assert task["progress_label"].startswith("抓取 1/4")


def test_prune_keeps_live_run_and_drops_finished(tmp_path) -> None:
    old = tmp_path / "run-old"
    old.mkdir()
    (old / "status.json").write_text(
        json.dumps({"pid": 1, "tasks": [{"status": "done"}]}),
        encoding="utf-8",
    )
    os.utime(old, (1, 1))
    alive = tmp_path / "run-alive"
    alive.mkdir()
    (alive / "status.json").write_text(
        json.dumps({"pid": os.getpid(), "tasks": [{"status": "running"}]}),
        encoding="utf-8",
    )
    removed = prune_runs(tmp_path, keep=0, days=0)
    assert removed == ["run-old"]
    assert alive.is_dir()
