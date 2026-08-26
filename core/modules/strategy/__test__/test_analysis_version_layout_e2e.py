"""simulate + sa 在新版 ``simulations/{vid}/{step}/`` 布局下的端到端。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.engines.analyzer.auto_run import maybe_run_after_simulate
from core.modules.strategy.core.engines.analyzer.consts import ANALYSIS_SUBDIR, REPORT_JSON
from core.modules.strategy.core.engines.analyzer.pipeline import AnalyzerPipeline
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    EntityInvestmentCsv,
    EnumerateStore,
)
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

pytestmark = pytest.mark.force_run


def _write_runtime(step_dir: Path) -> None:
    ArtifactIO.write_json(
        step_dir / "runtime_env.json",
        {
            "strategy_key": "rsi_v1",
            "strategy_path": "demo/regression/rsi/rsi_v1_baseline",
            "version_id": int(step_dir.parent.name),
            "fingerprints": {"settings": "s", "env": "e"},
            "period": {"start_date": "20230101", "end_date": "20260101"},
            "settings": {
                "effective_settings": {
                    "core": {"rsi_oversold_threshold": 20},
                    "data": {
                        "base": {
                            "data_key": "stock.kline.daily",
                            "indicators": {"rsi": [{"length": 14}]},
                        }
                    },
                    "goal": {"stop_loss": {"stages": [{"ratio": -0.2}]}},
                    "simulation": {"execution": {"mode": "entity_based"}},
                }
            },
        },
    )
    (step_dir / "entity_ids.txt").write_text("688005.SH\n", encoding="utf-8")


def _write_enum_entity(step_dir: Path) -> None:
    store = EnumerateStore.at(step_dir, version_id=step_dir.parent.name)
    store.write_investments(
        EntityInvestmentCsv.build(
            "688005.SH",
            [
                {
                    "meta": {"opportunity_id": "1"},
                    "trigger_date": "20240102",
                    "trigger_price": 10.0,
                    "lifecycle": "complete",
                    "entry": {"date": "20240103", "price": 10.1},
                    "exit_info": {
                        "date": "20240201",
                        "price": 11.0,
                        "reason": "take_profit",
                    },
                    "holding": {"days": 20},
                    "outcome": {"result": "win", "weighted_roi": 0.08},
                    "capture": {"rsi": 18.0},
                },
                {
                    "meta": {"opportunity_id": "2"},
                    "trigger_date": "20240302",
                    "trigger_price": 9.5,
                    "lifecycle": "complete",
                    "entry": {"date": "20240303", "price": 9.6},
                    "exit_info": {
                        "date": "20240401",
                        "price": 10.2,
                        "reason": "take_profit",
                    },
                    "holding": {"days": 18},
                    "outcome": {"result": "loss", "weighted_roi": -0.03},
                    "capture": {"rsi": 22.0},
                },
            ],
        )
    )


def test_analyzer_pipeline_writes_under_vid_step_layout(tmp_path: Path) -> None:
    strategy_folder = tmp_path / "demo" / "rsi"
    enum_dir = strategy_folder / "results" / "simulations" / "3" / "enum"
    enum_dir.mkdir(parents=True)
    _write_runtime(enum_dir)
    _write_enum_entity(enum_dir)

    store = ArtifactStore.resolve(
        strategy_folder,
        kind=SimulateKind.ENUMERATE,
        version_id="3",
    )
    out = AnalyzerPipeline.run(store)

    report_path = enum_dir / ANALYSIS_SUBDIR / REPORT_JSON
    assert report_path.is_file()
    assert out["report_path"] == str(report_path.resolve())
    report = ArtifactIO.read_json(report_path)
    assert isinstance(report.get("insights"), dict)
    assert str(report["insights"].get("headline") or "").strip()


def test_maybe_run_after_simulate_resolves_version_id(tmp_path: Path) -> None:
    strategy_folder = tmp_path / "demo" / "rsi"
    enum_dir = strategy_folder / "results" / "simulations" / "3" / "enum"
    enum_dir.mkdir(parents=True)
    _write_runtime(enum_dir)
    _write_enum_entity(enum_dir)

    with patch(
        "core.modules.strategy.core.services.discovery.DiscoveryService.resolve_strategy_folder",
        return_value=strategy_folder,
    ):
        out = maybe_run_after_simulate(
            "demo/rsi",
            step="enum",
            simulate_result={"enumerate": {"success": True, "version_id": "3"}},
            effective_settings={"analysis": {"enabled": True}},
        )

    assert out.get("skipped") is False
    assert "simulations/3/enum/analysis" in str(out.get("report_path") or "")
