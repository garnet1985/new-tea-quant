"""ClassDiscovery 包内单测（临时包，不依赖 userspace）。"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from core.infra.discovery.core.class_discovery import ClassDiscovery, DiscoveryConfig

pytestmark = pytest.mark.force_run


@pytest.fixture()
def plugin_pkg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "disc_plugins_root"
    root.mkdir()
    pkg = root / "disc_plugins"
    (pkg / "alpha").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "alpha" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "alpha" / "plugin.py").write_text(
        textwrap.dedent(
            """
            class BasePlugin:
                plugin_name = None

            class AlphaPlugin(BasePlugin):
                plugin_name = "alpha"
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(root))
    for name in list(sys.modules):
        if name == "disc_plugins" or name.startswith("disc_plugins."):
            del sys.modules[name]
    return root


def test_discover_with_config(plugin_pkg: Path):
    from disc_plugins.alpha.plugin import BasePlugin

    config = DiscoveryConfig(
        base_class=BasePlugin,
        module_name_pattern="{base_module}.{name}.plugin",
        key_extractor=lambda cls: getattr(cls, "plugin_name", None),
        class_filter=lambda cls: bool(getattr(cls, "plugin_name", None)),
    )
    discovery = ClassDiscovery(config)
    result = discovery.discover("disc_plugins")
    assert "alpha" in result.classes
    assert result.classes["alpha"].__name__ == "AlphaPlugin"


def test_cache_mechanism(plugin_pkg: Path):
    from disc_plugins.alpha.plugin import BasePlugin

    config = DiscoveryConfig(
        base_class=BasePlugin,
        module_name_pattern="{base_module}.{name}.plugin",
    )
    discovery = ClassDiscovery(config)
    result1 = discovery.discover("disc_plugins", use_cache=True)
    result2 = discovery.discover("disc_plugins", use_cache=True)
    assert result1.classes == result2.classes
    discovery.clear_cache("disc_plugins")
    result3 = discovery.discover("disc_plugins", use_cache=True)
    assert len(result1.classes) == len(result3.classes)


def test_discover_class_by_path_static(plugin_pkg: Path):
    from disc_plugins.alpha.plugin import BasePlugin, AlphaPlugin

    cls = ClassDiscovery.discover_class_by_path(
        "disc_plugins.alpha.plugin.AlphaPlugin",
        base_class=BasePlugin,
    )
    assert cls is AlphaPlugin
    assert (
        ClassDiscovery.discover_class_by_path(
            "disc_plugins.alpha.plugin.Missing",
            base_class=BasePlugin,
        )
        is None
    )
