"""扫描结果过期判定：设置指纹 / 工作台版本。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.scanner.pipeline import ScannerPipeline
from core.modules.strategy.core.engines.scanner.report_manager import ReportManager

pytestmark = pytest.mark.force_run


def test_settings_stale_compares_fingerprint() -> None:
    assert ScannerPipeline._settings_stale({"scan_fingerprint": "a"}, "b") is True
    assert ScannerPipeline._settings_stale({"scan_fingerprint": "a"}, "a") is False
    assert ScannerPipeline._settings_stale({}, "a") is False
    assert ScannerPipeline._settings_stale({"scan_fingerprint": "a"}, "") is False


def test_version_stale_when_workbench_ahead() -> None:
    assert ScannerPipeline._version_stale({"workbench_version": 1}, 4) is True
    assert ScannerPipeline._version_stale({"workbench_version": 4}, 4) is False
    assert ScannerPipeline._version_stale({"workbench_version": 5}, 4) is False
    # 旧摘要无版本号，但当前已有工作台 → 视为过时
    assert ScannerPipeline._version_stale({}, 4) is True
    assert ScannerPipeline._version_stale({"workbench_version": 1}, 0) is False


def test_attach_scan_identity_copies_version_fields() -> None:
    report = ScannerPipeline._attach_scan_identity(
        {"date": "20240110", "total_opportunities": 0},
        {
            "strategy_key": "demo/foo",
            "workbench_version": 3,
            "scan_fingerprint": "fp1",
        },
        fallback_strategy_key="fallback",
    )
    assert report["strategy_key"] == "demo/foo"
    assert report["workbench_version"] == 3
    assert report["strategy_version"] == "v3"
    assert report["scan_fingerprint"] == "fp1"


def test_report_manager_begin_derives_strategy_version() -> None:
    mgr = ReportManager.begin(
        strategy_key="demo",
        scan_date="20240110",
        stock_ids=["600000.SH"],
        workbench_version=2,
    )
    assert mgr.workbench_version == 2
    assert mgr.strategy_version == "v2"
    out = mgr.to_report_dict()
    assert out["workbench_version"] == 2
    assert out["strategy_version"] == "v2"


def test_readiness_payload_includes_current_version() -> None:
    payload = ScannerPipeline._readiness_payload(
        primary_action="rerun",
        can_scan=True,
        settings_stale=False,
        version_stale=True,
        current_workbench_version=4,
        report={"strategy_version": "v1", "workbench_version": 1},
    )
    assert payload["primary_action"] == "rerun"
    assert payload["version_stale"] is True
    assert payload["current_workbench_version"] == 4
    assert payload["report"]["strategy_version"] == "v1"
