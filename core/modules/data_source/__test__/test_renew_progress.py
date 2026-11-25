"""数据更新把每个数据源写成进度树里的一层。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run


@pytest.fixture
def progress_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    from core.infra.progress.core import store
    from core.modules.data_source.core.progress import bind_renew_leaf

    store.reset()
    bind_renew_leaf("")
    yield tmp_path
    bind_renew_leaf("")
    store.reset()


def test_each_source_is_one_step(progress_dir, capsys):
    from core.infra.progress import Progress
    from core.modules.data_source.core.execution_scheduler import DataSourceExecutionScheduler
    from core.modules.data_source.core.progress import SyncProgress

    class Handler:
        def __init__(self, key):
            self.key = key

        def get_key(self):
            return self.key

    scheduler = DataSourceExecutionScheduler()
    scheduler.open_progress([Handler("cpi"), Handler("stock_list")], "data-renew-abc")
    scheduler.begin_source("cpi")
    SyncProgress("cpi").bundles(1, 4, 10)
    scheduler.finish_source("cpi")
    scheduler.begin_source("stock_list")
    scheduler.fail_source("stock_list", RuntimeError("超时"))
    scheduler.close_progress()

    root = Progress.read("data-renew-abc")
    assert root["job"] == "renew"
    assert root["status"] == "completed"
    assert root["ratio"] == 1.0
    assert root["done"] == 2
    assert root["total"] == 2
    assert root["steps"][0]["status"] == "completed"
    assert root["steps"][0]["done"] == 4
    assert root["steps"][1]["status"] == "failed"
    assert "超时" in root["steps"][1]["detail"]
    assert (progress_dir / "data-renew-abc.json").is_file()
    assert "抓取 1/4" in capsys.readouterr().out


def test_aborted_run_marks_the_root_failed(progress_dir):
    from core.infra.progress import Progress
    from core.modules.data_source.core.execution_scheduler import DataSourceExecutionScheduler

    class Handler:
        def get_key(self):
            return "cpi"

    scheduler = DataSourceExecutionScheduler()
    scheduler.open_progress([Handler()], "data-renew-fail")
    scheduler.begin_source("cpi")
    scheduler.fail_source("cpi", RuntimeError("断了"))
    scheduler.fail_progress(RuntimeError("断了"))

    root = Progress.read("data-renew-fail")
    assert root["status"] == "failed"
    assert root["steps"][0]["status"] == "failed"
    assert "断了" in root["detail"]


def test_sync_progress_prints_when_no_tree_is_open(progress_dir, capsys):
    from core.modules.data_source.core.progress import SyncProgress

    SyncProgress("cpi").page("sys_data_cpi", "CPI", 1, 3)
    assert "正在读取第 1 页" in capsys.readouterr().out
    assert list(progress_dir.iterdir()) == []
