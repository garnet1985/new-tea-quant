"""simulate 成功后自动 analyze。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.engines.analyzer.auto_run import (
    is_analysis_enabled,
    maybe_run_after_simulate,
)
from core.modules.strategy.core.engines.analyzer.consts import ANALYSIS_SUBDIR, REPORT_JSON
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

pytestmark = pytest.mark.force_run


def test_is_analysis_enabled() -> None:
    assert not is_analysis_enabled({})
    assert not is_analysis_enabled({"analysis": {"enabled": False}})
    assert is_analysis_enabled({"analysis": {"enabled": True}})


def test_fingerprint_diff_ignores_analysis() -> None:
    from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
        StrategySettings,
    )

    disk = {
        "is_enabled": True,
        "meta": {"key": "demo"},
        "core": {"n": 1},
    }
    user = {**disk, "analysis": {"enabled": True}, "core": {"n": 2}}
    diff = StrategySettings.fingerprint_diff(disk, user)
    assert "analysis" not in diff
    assert diff.get("core") == {"n": 2}


def test_maybe_run_skips_when_disabled(tmp_path: Path) -> None:
    out = maybe_run_after_simulate(
        "demo",
        step="enum",
        simulate_result={"enumerate": {"success": True, "output_dir": str(tmp_path)}},
        effective_settings={},
    )
    assert out == {"skipped": True, "reason": "disabled"}


def test_maybe_run_skips_when_report_exists(tmp_path: Path) -> None:
    analysis_dir = tmp_path / ANALYSIS_SUBDIR
    analysis_dir.mkdir(parents=True)
    ArtifactIO.write_json(analysis_dir / REPORT_JSON, {"insights": {"headline": "ok"}})

    out = maybe_run_after_simulate(
        "demo",
        step="enum",
        simulate_result={"enumerate": {"success": True, "output_dir": str(tmp_path)}},
        effective_settings={"analysis": {"enabled": True}},
    )
    assert out == {"skipped": True, "reason": "exists"}
