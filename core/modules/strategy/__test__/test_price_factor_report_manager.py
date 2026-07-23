"""price_factor ReportManager：runtime / overall 骨架落盘。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_consts import (
    ENTITY_IDS_FILE,
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.engines.price_factor.enum_data import load_enum_version
from core.modules.strategy.core.engines.price_factor.report_manager import (
    EntityInvestments,
    PriceInvestmentRow,
    ReportManager,
    ReportPaths,
)

pytestmark = pytest.mark.force_run


def _write_enum_runtime(output_dir: Path, entity_ids: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ENTITY_IDS_FILE).write_text(
        "\n".join(entity_ids) + "\n",
        encoding="utf-8",
    )
    payload = {
        "strategy_key": "rsi_v1",
        "strategy_path": "demo/regression/rsi/rsi_v1_without_value_anchor",
        "version_id": 1,
        "execution_mode": "entity_based",
        "market_profile": "china_a_stock",
        "period": {"start_date": "20240102", "end_date": "20240110"},
        "settings_fp": "s",
        "env_fp": "e",
        "system": {},
        "settings_snapshot": {"effective_settings": {}, "settings_diff": {}},
    }
    (output_dir / RUNTIME_ENV_FILE).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_report_manager_finalize_writes_globals(tmp_path: Path, monkeypatch) -> None:
    enum_dir = tmp_path / "enum" / "1"
    _write_enum_runtime(enum_dir, ["000001.SZ"])
    data = load_enum_version(enum_dir, "1")

    price_root = tmp_path / "price"
    monkeypatch.setattr(
        "core.modules.strategy.core.engines.price_factor.report_manager.report_manager.ProjectContext.path.get_strategy_directory_simulation_price",
        lambda _name: price_root,
    )

    ctx = SimpleNamespace(
        strategy_info=SimpleNamespace(
            key="rsi_v1",
            unique_relative_path="demo/regression/rsi/rsi_v1_without_value_anchor",
        ),
        strategy_key="demo/regression/rsi/rsi_v1_without_value_anchor",
        settings_fp="sfp",
        env_fp="efp",
    )
    report = ReportManager.begin(ctx, data, start="20240102", end="20240110")
    EntityInvestments.save(
        report.output_dir,
        "000001.SZ",
        [
            PriceInvestmentRow(
                opportunity_id="opp_1",
                buy_date="20240103",
                buy_price=10.0,
                sell_date="20240105",
                sell_price=11.0,
                roi=0.1,
                holding_days=2,
                result="win",
            )
        ],
    )
    result = report.finalize(SimpleNamespace(success=True, total_jobs=1, completed_jobs=1, failed_jobs=0, elapsed_seconds=1.2), data=data)

    assert result["success"] is True
    assert result["summary"]["total_investments"] == 1
    assert result["summary"]["total_win"] == 1
    assert ReportPaths.runtime_env_path(report.output_dir).is_file()
    assert ReportPaths.overall_report_path(report.output_dir).is_file()
    assert ReportPaths.entity_ids_path(report.output_dir).is_file()
    assert ReportPaths.investments_csv(report.output_dir, "000001.SZ").is_file()
