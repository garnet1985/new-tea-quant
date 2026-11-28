"""import_data 进度挂到任务表：根 id 为固定 ``import``。"""

from __future__ import annotations

import pytest

from core.infra.job_pipeline.core import progress_view
from core.infra.progress import Progress

pytestmark = pytest.mark.force_run


@pytest.fixture
def progress_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NTQ_PROGRESS_DIR", str(tmp_path))
    monkeypatch.setenv("NTQ_PROGRESS_FLUSH_DELAY", "0")
    Progress.reset_for_tests()
    yield tmp_path
    Progress.reset_for_tests()


def test_strategy_scan_candidates_use_scan_prefix():
    roots = progress_view.progress_root_candidates(
        {
            "job_id": "jid-1",
            "kind": "strategy_scan",
            "resource_key": "demo",
        }
    )
    assert roots[0] == "scan-demo-jid-1"
    assert "pipeline-demo-jid-1" not in roots
    assert "jid-1" in roots


def test_strategy_scan_reads_scan_root(progress_dir):
    Progress.start(
        "scan-demo-jid-1",
        job="scan",
        label="扫描",
        steps=[{"id": "scan-demo-jid-1:body", "label": "body"}],
    )
    Progress.tick(
        "scan-demo-jid-1:body",
        1,
        2,
        detail="扫描 1/2",
        log=False,
    )
    snap = progress_view.read_progress_snapshot_for_job(
        {
            "job_id": "jid-1",
            "kind": "strategy_scan",
            "resource_key": "demo",
        }
    )
    assert snap is not None
    assert snap["root_id"] == "scan-demo-jid-1"
    assert snap["percent"] == 50


def test_import_data_reads_fixed_import_root(progress_dir):
    Progress.start(
        "import",
        job="import",
        label="导入数据",
        steps=[{"id": "import:download", "label": "download"}],
    )
    Progress.tick(
        "import:download",
        2,
        5,
        source="download",
        detail="数据下载中… 2/5 包 · 10.0/40.0 MB（25%）",
        log=False,
    )

    snap = progress_view.read_progress_snapshot_for_job(
        {
            "job_id": "import-data-abc123",
            "kind": "import_data",
            "resource_key": "import_data",
        }
    )
    assert snap is not None
    assert snap["root_id"] == "import"
    assert snap["percent"] == 40
    assert "2/5 包" in str(snap.get("detail") or "")


def test_import_data_candidates_include_import():
    roots = progress_view.progress_root_candidates(
        {
            "job_id": "import-data-xyz",
            "kind": "import_data",
            "resource_key": "import_data",
        }
    )
    assert roots[0] == "import"
    assert "import-data-xyz" in roots


def test_import_data_falls_back_to_install_progress(progress_dir):
    from core.infra.setup import Setup
    from core.infra.setup.core.shared.install_progress import (
        begin_import_download,
        tick_import_download,
    )

    progress_view.set_import_progress_reader(Setup.runtime.read_import_progress)
    try:
        begin_import_download(total_bytes=100)
        tick_import_download(40, 100, parts_done=1, parts_total=2)
        snap = progress_view._snapshot_from_import_progress()
        assert snap is not None
        assert snap["percent"] == 40
        assert "1/2 包" in str(snap.get("detail") or "")
    finally:
        progress_view.set_import_progress_reader(None)
