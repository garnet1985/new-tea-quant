"""ResultsRetention facade helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

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
    ), patch(
        "core.modules.strategy.core.services.results_retention.results_retention.ProjectContext"
    ) as pc:
        pc.path.get_strategy_simulation_enum_directory.return_value = enum_root
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


def test_normalize_kinds_rejects_unknown() -> None:
    try:
        ResultsRetention._normalize_kinds("full")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unsupported" in str(exc)
