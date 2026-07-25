"""price_factor JobExecutor：子进程加载本 batch 枚举 CSV。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.price_factor.enum_input.investments import (
    GoalAchievementRow,
    GoalAchievementCsv,
    InvestmentRow,
    EntityInvestmentCsv,
)
from core.modules.strategy.core.engines.price_factor.executor import JobExecutor
from core.modules.strategy.core.engines.price_factor.job_builder import PRICE_FACTOR_GLOBAL_KEY
from core.modules.strategy.core.engines.price_factor.report_manager import EntityInvestments

pytestmark = pytest.mark.force_run


def _write_enum_csv(output_dir: Path, entity_id: str) -> None:
    EntityInvestmentCsv(
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
    GoalAchievementCsv(
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
    init = JobExecutor._load_batch_enum_data(job_context)

    assert set(init["entities"]) == {"000001.SZ", "000002.SZ"}
    assert len(init["entities"]["000001.SZ"]["investments"].rows) == 1
    assert len(init["entities"]["000001.SZ"]["goals"].rows) == 1
    assert init["entities"]["000002.SZ"]["investments"].rows[0].investment_id == (
        "opp-000002.SZ"
    )


def test_load_batch_enum_data_missing_goals_ok(tmp_path: Path) -> None:
    EntityInvestmentCsv(
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
    init = JobExecutor._load_batch_enum_data(
        SimpleNamespace(job_id="b", payload=payload)
    )
    assert init["entities"]["000003.SZ"]["goals"].rows == []


def test_replay_and_save_batch(tmp_path: Path) -> None:
    enum_dir = tmp_path / "enum"
    price_dir = tmp_path / "price"
    _write_enum_csv(enum_dir, "000001.SZ")
    # overlapping second opp should be locked out
    EntityInvestmentCsv(
        entity_id="000001.SZ",
        rows=[
            InvestmentRow(
                investment_id="opp-a",
                trigger_date="20240102",
                entry_date="20240103",
                entry_price=10.0,
                exit_date="20240120",
                exit_price=11.0,
                lifecycle="complete",
                result="win",
                weighted_roi=0.1,
                holding_days=10,
            ),
            InvestmentRow(
                investment_id="opp-b",
                trigger_date="20240105",
                entry_date="20240106",
                entry_price=10.0,
                exit_date="20240108",
                exit_price=9.0,
                lifecycle="complete",
                result="loss",
                weighted_roi=-0.1,
                holding_days=2,
            ),
        ],
    ).save(enum_dir)

    payload = {
        "entity_specified": [{"id": "000001.SZ"}],
        "global": {
            PRICE_FACTOR_GLOBAL_KEY: {
                "enum_output_dir": str(enum_dir),
                "price_output_dir": str(price_dir),
                "enum_version_id": "1",
                "start_date": "20240102",
                "end_date": "20240131",
            }
        },
    }
    ctx = SimpleNamespace(job_id="batch_0", payload=payload, init={})
    ctx.init = JobExecutor._load_batch_enum_data(ctx)
    stats = JobExecutor._replay_and_save_batch(ctx)
    assert stats["investments"] == 1
    saved = EntityInvestments.load(price_dir, "000001.SZ")
    assert len(saved) == 1
    assert saved[0].opportunity_id == "opp-a"
