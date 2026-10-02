"""AttributionGroupStore.record_version 按样本窗记账。"""
from __future__ import annotations

from core.modules.strategy.core.engines.analyzer.steps.campaign.persist import (
    AttributionGroupStore,
)

import pytest

pytestmark = pytest.mark.force_run


def test_record_version_indexes_sample_window(tmp_path) -> None:
    root = tmp_path / "attribution"
    first = AttributionGroupStore.record_version(
        root,
        "env-a",
        "3",
        start_date="20200101",
        end_date="20231231",
        entity_ids=["600000.SH", "000001.SZ"],
    )
    assert first["group_id"] == "1"
    assert first["versions"] == ["3"]
    assert len(first["samples"]) == 1
    sample = first["samples"][0]
    assert sample["start_date"] == "20200101"
    assert sample["end_date"] == "20231231"
    assert sample["versions"] == ["3"]

    again = AttributionGroupStore.record_version(
        root,
        "env-a",
        "v3",
        start_date="20200101",
        end_date="20231231",
        entity_ids=["000001.SZ", "600000.SH"],
    )
    assert again["group_id"] == "1"
    assert again["versions"] == ["3"]
    assert len(again["samples"]) == 1

    other = AttributionGroupStore.record_version(
        root,
        "env-a",
        "4",
        start_date="20240101",
        end_date="20241231",
        entity_ids=["600000.SH"],
    )
    assert other["versions"] == ["3", "4"]
    assert len(other["samples"]) == 2
    assert other["samples"][1]["versions"] == ["4"]


def test_record_version_skips_empty_id(tmp_path) -> None:
    root = tmp_path / "attribution"
    assert AttributionGroupStore.record_version(root, "env-a", "") == {}
    assert not (root / "1").exists()
