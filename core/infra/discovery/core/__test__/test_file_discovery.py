"""FileDiscovery 包内单测。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.discovery.core.file_discovery import FileDiscovery, FileDiscoveryConfig

pytestmark = pytest.mark.force_run


def test_cache_key_includes_max_depth(tmp_path: Path):
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    deep = tmp_path / "l1" / "l2" / "l3"
    deep.mkdir(parents=True)
    (deep / "deep.json").write_text("{}", encoding="utf-8")

    shallow = FileDiscovery(
        FileDiscoveryConfig(
            base_dir=tmp_path,
            pattern="**/*.json",
            file_type="file",
            max_depth=1,
        )
    )
    deep_disc = FileDiscovery(
        FileDiscoveryConfig(
            base_dir=tmp_path,
            pattern="**/*.json",
            file_type="file",
            max_depth=10,
        )
    )
    assert len(shallow.discover()) == 1
    assert len(deep_disc.discover()) >= 2
