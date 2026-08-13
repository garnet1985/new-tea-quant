"""EnumeratorPipeline 主线门闸（不跑 BE 全链路）。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.modules.strategy.core.engines.enumerator.pipeline import EnumeratorPipeline

pytestmark = pytest.mark.force_run


def test_enumerator_pipeline_rejects_unknown_execution_mode() -> None:
    ctx = MagicMock()
    ctx.strategy_info.get_execution_mode.return_value = "bogus_mode"
    with pytest.raises(ValueError, match="不支持的execution_mode"):
        EnumeratorPipeline.run(ctx)


def test_enumerator_pipeline_to_report_empty_is_failure() -> None:
    assert EnumeratorPipeline._to_report(None) == {
        "success": False,
        "failed_entities": [],
    }
    assert EnumeratorPipeline._to_report({})["success"] is False


def test_enumerator_pipeline_mode_job_stack_slice_vs_entity() -> None:
    slice_builder, slice_executor, _ = EnumeratorPipeline._mode_job_stack("slice_based")
    assert "Slice" in slice_builder.__name__
    assert "Slice" in slice_executor.__name__

    entity_builder, entity_executor, _ = EnumeratorPipeline._mode_job_stack(
        "entity_based"
    )
    assert "Entity" in entity_builder.__name__
    assert "Entity" in entity_executor.__name__
