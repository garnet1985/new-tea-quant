"""API contract tests for infra.progress."""
from __future__ import annotations

import json

import pytest

from core.infra.progress import Progress
from core.infra.progress.contracts import ProgressSnapshot

pytestmark = pytest.mark.force_run


def test_package_exports_only_progress() -> None:
    import core.infra.progress as pkg

    assert pkg.__all__ == ["Progress"]
    assert callable(Progress.open)
    assert callable(Progress.step)
    assert callable(Progress.sub)
    assert callable(Progress.close)
    assert callable(Progress.read)
    assert callable(Progress.fraction)
    assert Progress.types.Snapshot is ProgressSnapshot


def test_fraction_adds_the_current_substep() -> None:
    assert Progress.fraction(5, 19) == 5 / 19
    assert Progress.fraction(5, 19, 4, 10) == (5 + 0.4) / 19
    assert Progress.fraction(0, 0) == 0.0
    assert Progress.fraction(3, 1) == 1.0


def test_step_resets_sub_and_close_finishes(tmp_path, monkeypatch) -> None:
    path = tmp_path / "progress.json"
    monkeypatch.setenv("NTQ_PROGRESS_FILE", str(path))
    monkeypatch.setattr("core.infra.progress.core.store._MEMORY", None)

    Progress.open("stock_list", 2, job="renew")
    Progress.sub(1, 4, source="stock_list")
    Progress.step(1, 2, source="cpi", job="renew")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["source"] == "cpi"
    assert payload["step"] == 1
    assert payload["step_total"] == 2
    assert payload["sub"] == 0
    assert payload["job"] == "renew"

    Progress.close()
    done = Progress.read()
    assert done["step"] == 2
    assert done["sub"] == 0
