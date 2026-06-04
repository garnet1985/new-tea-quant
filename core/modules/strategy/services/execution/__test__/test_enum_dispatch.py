from __future__ import annotations

from unittest.mock import patch

import pytest

from core.modules.strategy.engines.simulator.enumerator.data_classes.settings import (
    OpportunityEnumeratorSettings,
)
from core.modules.strategy.services.execution.enum_dispatch import (
    resolve_entities_per_job,
    resolve_enum_dispatch_plan,
)


def _enum_settings(raw: dict) -> OpportunityEnumeratorSettings:
    return OpportunityEnumeratorSettings.from_raw("example", {"enumerator": raw})


def test_explicit_entities_per_job():
    settings = _enum_settings({"entities_per_job": 50, "max_workers": 4})
    assert resolve_entities_per_job(total_stocks=100, enum_settings=settings) == 50


@patch(
    "core.infra.worker.dispatch_planner._get_virtual_memory_mb",
    return_value=(16384.0, 8192.0),
)
def test_auto_with_measured_mb(mock_vm):
    settings = _enum_settings({"entities_per_job": "auto", "max_workers": "auto"})
    plan = resolve_enum_dispatch_plan(
        total_stocks=1000,
        enum_settings=settings,
        measured_mb_per_entity=1.2,
    )
    assert plan.source_entities_per_job == "auto"
    assert plan.source_mb_per_entity == "probe"
    assert plan.max_workers >= 1


def test_auto_without_probe_raises():
    settings = _enum_settings({"entities_per_job": "auto", "dispatch_probe": False})
    with pytest.raises(ValueError, match="探针"):
        resolve_enum_dispatch_plan(total_stocks=100, enum_settings=settings)
