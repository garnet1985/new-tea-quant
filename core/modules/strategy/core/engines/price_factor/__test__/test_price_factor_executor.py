"""price_factor PriceFactorJobExecutor：子进程加载本 batch 枚举结果。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.shared.enum_result_contract import (
    CompletedGoal,
    EnumResult,
    EnumResultsManager,
)
from core.modules.strategy.core.services.artifacts import (
    PriceFactorStore,
)
from core.modules.strategy.core.engines.price_factor.executor import PriceFactorJobExecutor
from core.modules.strategy.core.engines.price_factor.job_builder import PRICE_FACTOR_GLOBAL_KEY

pytestmark = pytest.mark.force_run


def _write_enum_json(
    output_dir: Path,
    entity_id: str,
    *results: EnumResult,
) -> None:
    manager = EnumResultsManager.at(output_dir)
    manager.accept(entity_id, results)
    manager.persist(entity_id)


def _payload(
    output_dir: Path,
    entity_ids: list[str],
    *,
    price_output_dir: Path | None = None,
) -> dict:
    meta = {
        "enum_output_dir": str(output_dir),
        "enum_version_id": "1",
        "start_date": "20240102",
        "end_date": "20240110",
        "timeline_point_count": 5,
    }
    if price_output_dir is not None:
        meta["price_output_dir"] = str(price_output_dir)
        meta["end_date"] = "20240131"
    return {
        "entity_specified": [{"id": eid} for eid in entity_ids],
        "global": {PRICE_FACTOR_GLOBAL_KEY: meta},
    }


def _filled_result(
    entity_id: str,
    *,
    investment_id: str = "",
    entry_date: str = "20240103",
    exit_date: str = "20240120",
    exit_price: float = 11.0,
    weighted_roi: float = 0.1,
    result: str = "win",
    goal_date: str = "",
) -> EnumResult:
    inv_id = investment_id or f"opp-{entity_id}"
    day = goal_date or exit_date
    return EnumResult(
        entity_id=entity_id,
        investment_id=inv_id,
        trigger_date="20240102",
        entry_date=entry_date,
        entry_price=10.0,
        exit_date=exit_date,
        exit_price=exit_price,
        lifecycle="complete",
        result=result,
        weighted_roi=weighted_roi,
        holding_days=10,
        completed_goals=(
            CompletedGoal(
                name="take_profit",
                date=day,
                price=exit_price,
                exit_ratio=1.0,
                profit=1.0,
                weighted_profit=1.0,
                reason="take_profit",
                roi=weighted_roi,
            ),
        ),
    )


def test_load_batch_enum_data(tmp_path: Path) -> None:
    _write_enum_json(
        tmp_path,
        "000001.SZ",
        _filled_result(
            "000001.SZ",
            exit_date="20240110",
            goal_date="20240110",
        ),
    )
    _write_enum_json(tmp_path, "000002.SZ", _filled_result("000002.SZ"))

    init = PriceFactorJobExecutor._load_batch_enum_data(
        SimpleNamespace(
            job_id="batch_0",
            payload=_payload(tmp_path, ["000001.SZ", "000002.SZ"]),
        )
    )

    assert set(init["entities"]) == {"000001.SZ", "000002.SZ"}
    first = init["entities"]["000001.SZ"]["results"]
    assert len(first) == 1
    assert first[0].investment_id == "opp-000001.SZ"
    assert first[0].completed_goals[0].date == "20240110"
    assert init["entities"]["000002.SZ"]["results"][0].investment_id == (
        "opp-000002.SZ"
    )


def test_load_batch_enum_data_missing_goals_ok(tmp_path: Path) -> None:
    _write_enum_json(
        tmp_path,
        "000003.SZ",
        EnumResult(
            entity_id="000003.SZ",
            investment_id="opp-3",
            trigger_date="20240102",
            entry_date="20240103",
            entry_price=1.0,
            lifecycle="open",
        ),
    )
    init = PriceFactorJobExecutor._load_batch_enum_data(
        SimpleNamespace(
            job_id="b",
            payload=_payload(tmp_path, ["000003.SZ"]),
        )
    )
    rows = init["entities"]["000003.SZ"]["results"]
    assert len(rows) == 1
    assert rows[0].investment_id == "opp-3"
    assert rows[0].completed_goals == ()


def test_replay_and_save_batch_from_json(tmp_path: Path) -> None:
    enum_dir = tmp_path / "enum"
    price_dir = tmp_path / "price"
    _write_enum_json(
        enum_dir,
        "000001.SZ",
        _filled_result("000001.SZ", investment_id="opp-a"),
        _filled_result(
            "000001.SZ",
            investment_id="opp-b",
            entry_date="20240106",
            exit_date="20240108",
            exit_price=9.0,
            weighted_roi=-0.1,
            result="loss",
            goal_date="20240108",
        ),
    )

    ctx = SimpleNamespace(
        job_id="batch_0",
        payload=_payload(enum_dir, ["000001.SZ"], price_output_dir=price_dir),
        init={},
    )
    ctx.init = PriceFactorJobExecutor._load_batch_enum_data(ctx)
    stats = PriceFactorJobExecutor._replay_and_save_batch(ctx)
    assert stats["investments"] == 1
    saved = PriceFactorStore.at(price_dir).investments("000001.SZ")
    assert [row.opportunity_id for row in saved] == ["opp-a"]
    goals = PriceFactorStore.at(price_dir).goals("000001.SZ")
    assert len(goals) == 1
    assert goals[0].investment_id == "opp-a"
    assert goals[0].date == "20240120"
    assert "completed_goals" not in saved[0].to_dict()
