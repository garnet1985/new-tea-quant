"""磁盘 simulate cache（SimulationVersionStore）。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import (
    RUNTIME_ENV_FILE,
    ArtifactStore,
    SimulationVersionStore,
)

pytestmark = pytest.mark.force_run


def test_disk_cache_hit(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    step_dir = root / "1" / "enum"
    step_dir.mkdir(parents=True)
    (step_dir / RUNTIME_ENV_FILE).write_text(
        json.dumps({"strategy_key": "demo"}),
        encoding="utf-8",
    )
    (root / "meta.json").write_text(
        json.dumps(
            {
                "registry": {
                    "1": {
                        "execute_fp": "s",
                        "env_fp": "e",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    fps = SimpleNamespace(
        execute_fp="s", env_fp="e", entity_ids=[], effective_settings=MagicMock()
    )

    with patch.object(ArtifactStore, "simulations_root", return_value=root), patch.object(
        ArtifactStore,
        "resolve",
        return_value=ArtifactStore.at(step_dir, kind=SimulateKind.ENUMERATE, version_id="1"),
    ):
        cached = SimulationVersionStore.get_cache(tmp_path, fps, SimulateKind.ENUMERATE)
    assert cached is not None
    assert cached["enumerate"]["version_id"] == "1"
    assert cached["enumerate"]["success"] is True
    assert cached["enumerate"]["output_dir"] == str(step_dir)
    assert "enumMetrics" not in cached["enumerate"]
    assert "priceMetrics" not in cached["enumerate"]
    assert "capitalMetrics" not in cached["enumerate"]


def test_disk_cache_miss_when_env_invalid(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    step_dir = root / "1" / "enum"
    step_dir.mkdir(parents=True)
    (step_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    (root / "meta.json").write_text(
        json.dumps(
            {
                "registry": {
                    "1": {
                        "execute_fp": "s",
                        "env_fp": "old-env",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    fps = SimpleNamespace(
        execute_fp="s", env_fp="new-env", entity_ids=[], effective_settings={}
    )

    with patch.object(ArtifactStore, "simulations_root", return_value=root):
        cached = SimulationVersionStore.get_cache(tmp_path, fps, SimulateKind.ENUMERATE)
    assert cached is None


def test_version_cache_does_not_import_engines() -> None:
    import core.modules.strategy.core.services.artifacts.version_cache as mod

    text = Path(mod.__file__).read_text(encoding="utf-8")
    assert "engines" not in text
    assert "OverallReport" not in text
    assert "StrategySettings" not in text
