from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.bff.APIs.strategy.routes.folder.implementer import (
    StrategyFolderImplementer,
    _ensure_under_strategies,
)


def test_ensure_under_strategies_accepts_nested_dir(tmp_path: Path):
    root = tmp_path / "strategies"
    folder = root / "demo" / "x"
    folder.mkdir(parents=True)
    with patch(
        "core.bff.APIs.strategy.routes.folder.implementer.ProjectContext.path.get_strategies_root",
        return_value=root,
    ):
        assert _ensure_under_strategies(folder) == folder.resolve()


def test_ensure_under_strategies_rejects_outside(tmp_path: Path):
    root = tmp_path / "strategies"
    root.mkdir()
    outside = tmp_path / "other"
    outside.mkdir()
    with patch(
        "core.bff.APIs.strategy.routes.folder.implementer.ProjectContext.path.get_strategies_root",
        return_value=root,
    ):
        with pytest.raises(ValueError, match="userspace/strategies"):
            _ensure_under_strategies(outside)


def test_reveal_opens_resolved_folder(tmp_path: Path):
    root = tmp_path / "strategies"
    folder = root / "demo" / "x"
    folder.mkdir(parents=True)
    impl = StrategyFolderImplementer()
    with patch(
        "core.bff.APIs.strategy.routes.folder.implementer.Strategy.resolve_folder",
        return_value=folder,
    ), patch(
        "core.bff.APIs.strategy.routes.folder.implementer.ProjectContext.path.get_strategies_root",
        return_value=root,
    ), patch(
        "core.bff.APIs.strategy.routes.folder.implementer.reveal_directory",
    ) as reveal:
        out = impl.reveal("demo/x")
    reveal.assert_called_once_with(folder.resolve())
    assert out["opened"] is True
    assert out["path"] == str(folder.resolve())
