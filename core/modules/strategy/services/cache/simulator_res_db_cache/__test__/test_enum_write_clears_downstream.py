"""enum 槽位写入时剔除下游 price / capital 槽位。"""

from unittest.mock import MagicMock

from core.modules.strategy.enums import Simulator
from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
    SimulatorResDbCacheService,
)


def test_set_cache_enum_write_clears_downstream_slots():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = [
        {
            "version": 3,
            "result_report": {
                "enum": {"opportunities": 10},
                "price_factor": {"win_rate": 50.0},
                "capital_allocation": {"total_return": 0.1},
            },
        }
    ]
    svc = SimulatorResDbCacheService()
    svc.table_operator = model

    sid = svc.set_cache(
        strategy_name="demo",
        settings_diff={"meta": {}},  # 差异字段
        simulator=Simulator.ENUMERATOR,
        simulator_report={"opportunities": 99},
        settings_fingerprint_id="sfp",
        env_fingerprint_id="efp",
    )

    assert sid == 3
    merged = model.update_result_report.call_args[0][2]
    assert merged["enum"] == {"opportunities": 99}
    assert "price_factor" not in merged
    assert "capital_allocation" not in merged


def test_set_cache_price_write_keeps_capital_slot():
    model = MagicMock()
    model.list_by_strategy_fingerprints.return_value = [
        {
            "version": 4,
            "result_report": {
                "enum": {"opportunities": 10},
                "capital_allocation": {"total_return": 0.2},
            },
        }
    ]
    svc = SimulatorResDbCacheService()
    svc.table_operator = model

    sid = svc.set_cache(
        strategy_name="demo",
        settings_diff={"meta": {}},  # 差异字段
        simulator=Simulator.PRICE_FACTOR,
        simulator_report={"win_rate": 60.0},
        settings_fingerprint_id="sfp",
        env_fingerprint_id="efp",
    )

    assert sid == 4
    merged = model.update_result_report.call_args[0][2]
    assert merged["price_factor"] == {"win_rate": 60.0}
    assert merged["capital_allocation"] == {"total_return": 0.2}
