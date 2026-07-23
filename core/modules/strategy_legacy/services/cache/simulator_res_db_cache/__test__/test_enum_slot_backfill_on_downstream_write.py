"""价格 / 资金落库时从磁盘补写缺失 ``enum`` 槽位。"""

from __future__ import annotations

from unittest.mock import MagicMock

from core.modules.strategy.enums import Simulator
from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
    SimulatorResDbCacheService,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.report_slot_disk_hydrate import (
    build_enum_slot_from_enumerator_dir,
    merge_enum_slot_if_missing_from_downstream,
)

_STRATEGY = "unit_test_strategy"


def test_build_enum_slot_from_enumerator_dir(enum_simulation_root):
    slot = build_enum_slot_from_enumerator_dir(_STRATEGY, "9")
    assert isinstance(slot, dict) and slot
    assert slot.get("enumerator_output_dir") == "9"
    assert int(slot.get("opportunities") or 0) > 0


def test_merge_enum_slot_if_missing_from_price_report(enum_simulation_root):
    price_report = {
        "win_rate": 73.8,
        "output_version": {"enumerator_output_dir": "9", "output_root": "enum"},
    }
    merged = merge_enum_slot_if_missing_from_downstream(
        _STRATEGY,
        {"price_factor": price_report},
        downstream_report=price_report,
        simulator_key="price_factor",
    )
    assert isinstance(merged.get("enum"), dict)
    assert merged["enum"].get("enumerator_output_dir") == "9"
    assert int(merged["enum"].get("opportunities") or 0) > 0


def test_set_cache_backfills_enum_when_creating_price_row(enum_simulation_root):
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = []
    model.create_snapshot.return_value = {"strategy_name": _STRATEGY, "version": 99}

    svc = SimulatorResDbCacheService.__new__(SimulatorResDbCacheService)
    svc.table_operator = model
    svc._row_retention = MagicMock()

    price_report = {
        "win_rate": 1.0,
        "output_version": {"enumerator_output_dir": "9", "output_root": "enum"},
    }
    sid = svc.set_cache(
        strategy_name=_STRATEGY,
        settings_diff={"goal": {}},  # 差异字段
        simulator=Simulator.PRICE_FACTOR,
        simulator_report=price_report,
        settings_fingerprint_id="sfp_test",
        env_fingerprint_id="efp_test",
    )
    assert sid == 99
    created = model.create_snapshot.call_args[0][2]
    assert isinstance(created.get("enum"), dict)
    assert created["enum"].get("enumerator_output_dir") == "9"
    assert isinstance(created.get("price_factor"), dict)
