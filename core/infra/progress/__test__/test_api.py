"""API contract tests for infra.progress."""
from __future__ import annotations

import json
import time

import pytest

from core.infra.progress import Progress
from core.infra.progress.contracts import ProgressNode
from core.infra.progress.core import store

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def progress_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    store.reset()
    yield tmp_path
    store.reset()


def test_package_exports_only_progress() -> None:
    import core.infra.progress as pkg

    assert pkg.__all__ == ["Progress"]
    assert callable(Progress.start)
    assert callable(Progress.tick)
    assert callable(Progress.finish)
    assert callable(Progress.fail)
    assert callable(Progress.cancel)
    assert callable(Progress.pause)
    assert callable(Progress.resume)
    assert callable(Progress.clear)
    assert callable(Progress.read)
    assert callable(Progress.latest)
    assert Progress.types.Node is ProgressNode


def test_tick_can_skip_the_log(capsys) -> None:
    Progress.start("quiet", job="scan")
    Progress.tick("quiet", 1, 2, log=False)
    assert capsys.readouterr().out == ""
    assert Progress.read("quiet")["ratio"] == 0.5


def test_leaf_tick_writes_ratio_and_log(progress_dir, capsys) -> None:
    Progress.start("scan-1", job="scan", label="扫描")
    Progress.tick("scan-1", 4, 10, detail="扫描 4/10")
    assert capsys.readouterr().out.strip() == "扫描 4/10"

    payload = json.loads((progress_dir / "scan-1.json").read_text(encoding="utf-8"))
    assert payload["job"] == "scan"
    assert payload["status"] == "running"
    assert payload["done"] == 4
    assert payload["total"] == 10
    assert payload["ratio"] == 0.4
    assert payload["detail"] == "扫描 4/10"
    assert payload["steps"] == []

    Progress.finish("scan-1")
    done = Progress.read("scan-1")
    assert done["status"] == "completed"
    assert done["ratio"] == 1
    assert done["done"] == 10


def test_nested_tick_finds_node_and_weights_parent(progress_dir) -> None:
    Progress.start(
        "run-1",
        job="renew",
        label="更新数据",
        steps=[
            {"id": "run-1:list", "label": "股票列表", "weight": 1},
            {"id": "run-1:daily", "label": "日线", "weight": 3},
        ],
    )
    Progress.finish("run-1:list")
    Progress.tick("run-1:daily", 5, 10, source="daily", detail="抓取 5/10")

    root = Progress.read("run-1:daily")
    assert root["id"] == "run-1"
    assert root["ratio"] == 0.625
    assert root["done"] == 1
    assert root["total"] == 2
    assert root["status"] == "running"
    daily = root["steps"][1]
    assert daily["status"] == "running"
    assert daily["source"] == "daily"
    assert daily["ratio"] == 0.5
    assert (progress_dir / "run-1.json").is_file()
    assert not (progress_dir / "run-1:daily.json").exists()


def test_fail_child_moves_parent_and_keeps_root_running() -> None:
    Progress.start(
        "run-2",
        job="renew",
        steps=[
            {"id": "run-2:a", "weight": 1},
            {"id": "run-2:b", "weight": 1},
        ],
    )
    Progress.fail("run-2:a", detail="日线失败")
    root = Progress.read("run-2")
    assert root["status"] == "running"
    assert root["ratio"] == 0.5
    assert root["steps"][0]["status"] == "failed"
    assert root["steps"][0]["detail"] == "日线失败"
    assert root["steps"][0]["ratio"] == 0


def test_pause_and_cancel_keep_ratio() -> None:
    Progress.start("job-3", job="install")
    Progress.tick("job-3", 1, 4)
    Progress.pause("job-3")
    paused = Progress.read("job-3")
    assert paused["status"] == "paused"
    assert paused["ratio"] == 0.25

    Progress.resume("job-3")
    assert Progress.read("job-3")["status"] == "running"

    Progress.cancel("job-3", detail="已取消")
    cancelled = Progress.read("job-3")
    assert cancelled["status"] == "cancelled"
    assert cancelled["ratio"] == 0.25
    assert cancelled["detail"] == "已取消"


def test_missing_node_raises_and_parent_tick_is_rejected() -> None:
    Progress.start("run-4", job="tag", steps=[{"id": "run-4:calc"}])
    with pytest.raises(FileNotFoundError):
        Progress.tick("missing", 1, 1)
    with pytest.raises(ValueError):
        Progress.tick("run-4", 1, 1)
    with pytest.raises(ValueError):
        Progress.start("bad/id", job="tag")


def test_latest_and_clear() -> None:
    Progress.start("old", job="scan", label="旧")
    Progress.tick("old", 1, 2)
    time.sleep(1)
    Progress.start("new", job="scan", label="新")
    assert Progress.latest("scan")["id"] == "new"
    assert Progress.latest("renew") is None
    assert Progress.read("missing") is None

    Progress.clear("new")
    assert Progress.read("new") is None
    assert Progress.read("old")["id"] == "old"


def test_prune_drops_old_finished_and_keeps_running(progress_dir) -> None:
    now = int(time.time())
    old = {
        "id": "old-done",
        "job": "renew",
        "status": "completed",
        "source": "",
        "label": "",
        "detail": "",
        "weight": 1,
        "done": 1,
        "total": 1,
        "ratio": 1,
        "started_at": now - 20 * 86400,
        "updated_at": now - 20 * 86400,
        "steps": [],
    }
    alive = dict(old)
    alive["id"] = "still-running"
    alive["status"] = "running"
    other = dict(old)
    other["id"] = "other-job"
    other["job"] = "scan"
    for node in (old, alive, other):
        (progress_dir / f"{node['id']}.json").write_text(
            json.dumps(node),
            encoding="utf-8",
        )

    Progress.start("fresh", job="renew")
    assert not (progress_dir / "old-done.json").exists()
    assert (progress_dir / "still-running.json").is_file()
    assert (progress_dir / "other-job.json").is_file()
    assert (progress_dir / "fresh.json").is_file()


def test_read_sees_tick_before_delayed_flush(progress_dir, monkeypatch) -> None:
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "30")
    Progress.start("slow", job="backtest")
    Progress.tick("slow", 1, 2, detail="回测 1/2")
    assert not (progress_dir / "slow.json").exists()
    assert Progress.read("slow")["ratio"] == 0.5
    store.drain()
    assert json.loads((progress_dir / "slow.json").read_text(encoding="utf-8"))["ratio"] == 0.5
