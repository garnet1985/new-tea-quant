"""price_factor JobExecutor：子进程加载本 batch 枚举 CSV。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
    GoalAchievementRow,
    GoalAchievements,
    InvestmentRow,
    StockInvestments,
)
from core.modules.strategy.core.engines.price_factor.executor import JobExecutor
from core.modules.strategy.core.engines.price_factor.job_builder import PRICE_FACTOR_GLOBAL_KEY

pytestmark = pytest.mark.force_run


def _write_enum_csv(output_dir: Path, entity_id: str) -> None:
    StockInvestments(
        entity_id=entity_id,
        rows=[
            InvestmentRow(
                investment_id=f"opp-{entity_id}",
                trigger_date="20240102",
                entry_date="20240103",
                entry_price=10.0,
                lifecycle="complete",
            )
        ],
    ).save(output_dir)
    GoalAchievements(
        entity_id=entity_id,
        rows=[
            GoalAchievementRow(
                investment_id=f"opp-{entity_id}",
                goal_name="take_profit",
                date="20240110",
                price=11.0,
                exit_ratio=1.0,
                profit=1.0,
                weighted_profit=1.0,
                reason="take_profit",
                roi=0.1,
            )
        ],
    ).save(output_dir)


def test_load_batch_enum_data(tmp_path: Path) -> None:
    _write_enum_csv(tmp_path, "000001.SZ")
    _write_enum_csv(tmp_path, "000002.SZ")

    payload = {
        "entity_specified": [{"id": "000001.SZ"}, {"id": "000002.SZ"}],
        "global": {
            PRICE_FACTOR_GLOBAL_KEY: {
                "enum_output_dir": str(tmp_path),
                "enum_version_id": "1",
                "start_date": "20240102",
                "end_date": "20240110",
                "timeline_point_count": 5,
            }
        },
    }
    job_context = SimpleNamespace(job_id="batch_0", payload=payload)
    init = JobExecutor.load_batch_enum_data(job_context)

    assert set(init["entities"]) == {"000001.SZ", "000002.SZ"}
    assert len(init["entities"]["000001.SZ"]["investments"].rows) == 1
    assert len(init["entities"]["000001.SZ"]["goals"].rows) == 1
    assert init["entities"]["000002.SZ"]["investments"].rows[0].investment_id == (
        "opp-000002.SZ"
    )


def test_load_batch_enum_data_missing_goals_ok(tmp_path: Path) -> None:
    StockInvestments(
        entity_id="000003.SZ",
        rows=[
            InvestmentRow(
                investment_id="opp-3",
                trigger_date="20240102",
                entry_date="20240103",
                entry_price=1.0,
                lifecycle="open",
            )
        ],
    ).save(tmp_path)
    payload = {
        "entity_specified": [{"id": "000003.SZ"}],
        "global": {
            PRICE_FACTOR_GLOBAL_KEY: {
                "enum_output_dir": str(tmp_path),
                "enum_version_id": "1",
                "start_date": "20240102",
                "end_date": "20240110",
                "timeline_point_count": 1,
            }
        },
    }
    init = JobExecutor.load_batch_enum_data(
        SimpleNamespace(job_id="b", payload=payload)
    )
    assert init["entities"]["000003.SZ"]["goals"].rows == []
