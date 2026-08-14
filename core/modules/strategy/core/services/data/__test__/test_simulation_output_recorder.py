"""SimulationOutputRecorder version allocate + prune."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)

pytestmark = pytest.mark.force_run


def test_prune_keeps_newest_n(tmp_path: Path) -> None:
    root = tmp_path / "price"
    for i in (1, 2, 3, 4, 5):
        (root / str(i)).mkdir(parents=True)

    deleted = SimulationOutputRecorder.prune_old_version_dirs(root, max_versions=2)
    assert deleted == 3
    remaining = sorted(
        int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit()
    )
    assert remaining == [4, 5]


def test_allocate_increments_and_prunes(tmp_path: Path) -> None:
    root = tmp_path / "portfolio"
    ids = []
    for _ in range(5):
        _dir, vid = SimulationOutputRecorder.allocate_version_dir(
            "demo/s",
            root,
            max_versions=3,
        )
        ids.append(vid)
    assert ids == [1, 2, 3, 4, 5]
    remaining = sorted(
        int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit()
    )
    assert remaining == [3, 4, 5]
