from __future__ import annotations

from unittest.mock import patch

import pytest

from core.modules.strategy.services.execution.enum_dispatch import (
    resolve_enum_dispatch_plan,
    resolve_entities_per_job,
)


@patch(
    "core.modules.strategy.services.execution.enum_dispatch.enumerator_dispatch_dict",
    return_value={"entities_per_job": 50},
)
def test_explicit_entities_per_job(_mock):
    assert resolve_entities_per_job(total_stocks=100) == 50


@patch(
    "core.infra.worker.dispatch_planner._get_virtual_memory_mb",
    return_value=(16384.0, 8192.0),
)
@patch(
    "core.modules.strategy.services.execution.enum_dispatch.enumerator_dispatch_dict",
    return_value={"entities_per_job": "auto", "dispatch_probe": True},
)
def test_auto_with_measured_mb(_mock_perf, mock_vm):
    plan = resolve_enum_dispatch_plan(
        total_stocks=1000,
        measured_mb_per_entity=1.2,
    )
    assert plan.source_entities_per_job == "smart_auto"
    assert plan.source_mb_per_entity == "probe"
    assert plan.max_workers >= 1


@patch(
    "core.modules.strategy.services.execution.enum_dispatch.enumerator_dispatch_dict",
    return_value={"entities_per_job": "auto", "dispatch_probe": False},
)
def test_auto_without_probe_raises(_mock):
    with pytest.raises(ValueError, match="探针"):
        resolve_enum_dispatch_plan(total_stocks=100)
