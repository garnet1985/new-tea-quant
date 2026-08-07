"""ModuleDiscovery 包内单测（临时包，不依赖 userspace）。"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from core.infra.discovery.core.module_discovery import ModuleDiscovery

pytestmark = pytest.mark.force_run


@pytest.fixture()
def schema_pkg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "disc_schema_root"
    root.mkdir()
    pkg = root / "disc_schemas"
    (pkg / "alpha").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "alpha" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "alpha" / "schema.py").write_text(
        textwrap.dedent(
            """
            SCHEMA = {"name": "alpha"}
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(root))
    for name in list(sys.modules):
        if name == "disc_schemas" or name.startswith("disc_schemas."):
            del sys.modules[name]
    return root


def test_discover_objects(schema_pkg: Path):
    objects = ModuleDiscovery.discover_objects(
        base_module_path="disc_schemas",
        object_name="SCHEMA",
        module_pattern="{base_module}.{name}.schema",
    )
    assert objects == {"alpha": {"name": "alpha"}}
