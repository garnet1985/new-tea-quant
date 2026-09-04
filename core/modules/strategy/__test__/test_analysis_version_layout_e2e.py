"""simulate + analyze 在新版 ``simulations/{vid}/{step}/`` 布局下的端到端。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.engines.analyzer import Analyzer
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    EntityInvestmentCsv,
    EnumerateStore,
)
from core.modules.strategy.core.services.artifacts.consts import (
    ANALYSIS_REPORT_JSON,
    ANALYSIS_SUBDIR,
)
from core.modules.strategy.core.services.artifacts.io import ArtifactIO
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

pytestmark = pytest.mark.force_run


def _write_runtime(step_dir: Path) -> None:
    ArtifactIO.write_json(
        step_dir / "runtime_env.json",
        {
            "strategy_key": "rsi_v1",
            "strategy_path": "demo/regression/rsi/rsi_v1_baseline",
            "version_id": int(step_dir.parent.name),
            "market_profile": "china_a_stock",
            "period": {"start_date": "20230101", "end_date": "20260101"},
        },
    )
    (step_dir / "entity_ids.txt").write_text("688005.SH\n", encoding="utf-8")
    root = step_dir.parent.parent
    vid = step_dir.parent.name
    VersionMetaStore.register_version(root, vid, execute_fp="s", env_fp="e")
    VersionMetaStore.write_version_archive(
        root,
        vid,
        full_settings={"core": {"rsi_oversold_threshold": 20}},
        effective_settings={
            "core": {"rsi_oversold_threshold": 20},
            "data": {
                "base": {
                    "data_key": "stock.kline.daily",
                    "indicators": {"rsi": [{"length": 14}]},
                }
            },
            "goal": {"stop_loss": {"stages": [{"ratio": -0.2}]}},
            "simulation": {"execution": {"mode": "entity_based"}},
        },
        entity_ids=["688005.SH"],
        start_date="20230101",
        end_date="20260101",
    )


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


def test_analyzer_run_writes_under_vid_step_layout(tmp_path: Path) -> None:
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
    out = Analyzer.run(store)

    report_path = enum_dir / ANALYSIS_SUBDIR / ANALYSIS_REPORT_JSON
    assert report_path.is_file()
    assert out["report_path"] == str(report_path.resolve())
    report = ArtifactIO.read_json(report_path)
    assert isinstance(report.get("insights"), dict)
    assert str(report["insights"].get("headline") or "").strip()
