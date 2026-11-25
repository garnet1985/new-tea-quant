"""发现扫描。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.series_relation.core.discovery.discovery_service import DiscoveryService

pytestmark = pytest.mark.force_run


def test_discover_settings(tmp_path: Path) -> None:
    folder = tmp_path / "demo"
    folder.mkdir()
    folder.joinpath("settings.py").write_text(
        """
settings = {
    "meta": {"key": "demo_rel", "display_name": "Demo"},
    "series": [
        {"data_key": "macro.lpr", "field": "lpr_1y"},
    ],
}
""",
        encoding="utf-8",
    )

    def lookup(key: str):
        return {"meta": {"type": "time_series", "scope": "global"}}

    found = DiscoveryService.discover(root=tmp_path, declaration_lookup=lookup)
    assert len(found) == 1
    assert found[0].key == "demo_rel"
    assert DiscoveryService.find("demo_rel", root=tmp_path, declaration_lookup=lookup)
