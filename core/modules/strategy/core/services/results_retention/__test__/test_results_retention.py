"""ResultsRetention facade helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.results_retention import ResultsRetention

pytestmark = pytest.mark.force_run


def test_prune_simulation_results_per_kind(tmp_path: Path) -> None:
    enum_root = tmp_path / "simulations" / "enum"
    for i in (1, 2, 3, 4):
        (enum_root / str(i)).mkdir(parents=True)

    with patch.object(
        ResultsRetention,
        "_resolve_folder",
        return_value=tmp_path,
    ), patch.object(
        ArtifactStore,
        "simulation_root",
        classmethod(lambda cls, folder, kind: enum_root),
    ):
        out = ResultsRetention.prune_simulation_results(
            "demo/x", kind="enum", max_versions=2
        )

    assert out["ok"] is True
    assert out["deleted_count"] == 2
    assert out["per_kind"]["enum"] == 2
    remaining = sorted(
        int(p.name) for p in enum_root.iterdir() if p.is_dir() and p.name.isdigit()
    )
    assert remaining == [3, 4]


def test_prune_rejects_unknown_kind(tmp_path: Path) -> None:
    with patch.object(ResultsRetention, "_resolve_folder", return_value=tmp_path):
        with pytest.raises(ValueError, match="unsupported"):
            ResultsRetention.prune_simulation_results("demo/x", kind="full")
