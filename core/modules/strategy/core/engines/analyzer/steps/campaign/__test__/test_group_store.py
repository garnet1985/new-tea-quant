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


def test_resolve_keeps_a_group_per_strategy_version(tmp_path) -> None:
    root = tmp_path / "attribution"
    first = AttributionGroupStore.resolve(root, "env-a", parent_version_id="1")
    second = AttributionGroupStore.resolve(root, "env-a", parent_version_id="2")
    again = AttributionGroupStore.resolve(root, "env-a", parent_version_id="1")
    assert first == "1"
    assert second == "2"
    assert again == "1"
    assert AttributionGroupStore.find_for_version(root, "env-a", "2") == "2"
    assert AttributionGroupStore.find_for_version(root, "env-a", "1") == "1"


def test_legacy_report_baseline_matches_its_version(tmp_path) -> None:
    root = tmp_path / "attribution" / "1" / "price"
    root.mkdir(parents=True)
    (root / "report.json").write_text(
        '{"baseline_version_id": "1"}',
        encoding="utf-8",
    )
    (root.parent / "group_meta.json").write_text(
        '{"env_fp": "env-a", "group_id": "1"}',
        encoding="utf-8",
    )
    attr = root.parent.parent
    assert AttributionGroupStore.find_for_version(attr, "env-a", "1") == "1"
    assert AttributionGroupStore.find_for_version(attr, "env-a", "2") is None
    fresh = AttributionGroupStore.resolve(attr, "env-a", parent_version_id="2")
    assert fresh == "2"
    assert AttributionGroupStore.find_for_version(attr, "env-a", "1") == "1"


def test_record_version_skips_empty_id(tmp_path) -> None:
    root = tmp_path / "attribution"
    assert AttributionGroupStore.record_version(root, "env-a", "") == {}
    assert not (root / "1").exists()
