"""安装按步骤记进度，导入按表记进度。完成数不含失败的表。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run


@pytest.fixture
def progress_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    from core.infra.progress.core import store

    store.reset()
    yield tmp_path
    store.reset()


def test_import_progress_counts_finished_tables_only(progress_dir):
    from core.infra.setup.core.install_progress import (
        begin_import_table,
        close_import,
        fail_import_table,
        finish_import_table,
        open_import,
        read_import_progress,
    )

    open_import(["cpi", "stock_list"], done_names=["cpi"])
    begin_import_table("stock_list")
    running = read_import_progress()
    assert running["running"] is True
    assert running["completedCount"] == 1
    assert running["totalTables"] == 2
    assert running["currentTable"] == "stock_list"
    assert running["ratio"] == 0.5

    fail_import_table("stock_list", "超时")
    begin_import_table("stock_list")
    retrying = read_import_progress()
    assert retrying["completedCount"] == 1
    assert retrying["currentTable"] == "stock_list"

    finish_import_table("stock_list")
    close_import()
    done = read_import_progress()
    assert done["running"] is False
    assert done["completedCount"] == 2
    assert done["currentTable"] == ""
    assert (progress_dir / "import.json").is_file()


def test_failed_install_step_stays_on_the_root(progress_dir):
    from core.infra.progress import Progress
    from core.infra.setup.core.install_progress import (
        begin_install_step,
        fail_install,
        open_install,
        pause_install_step,
    )

    open_install(["sys_req_check", "db_connection"], done_ids=["sys_req_check"])
    begin_install_step("db_connection")
    pause_install_step("db_connection")
    paused = Progress.read("install")
    assert paused["steps"][0]["status"] == "completed"
    assert paused["steps"][1]["status"] == "paused"
    assert paused["status"] == "running"

    begin_install_step("db_connection")
    fail_install("db_connection", "连不上\n详情")
    failed = Progress.read("install")
    assert failed["status"] == "failed"
    assert failed["steps"][1]["status"] == "failed"
    assert failed["detail"] == "连不上"
    assert (progress_dir / "install.json").is_file()
