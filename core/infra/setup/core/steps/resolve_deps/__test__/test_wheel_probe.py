"""resolve_deps：仅 Python 3.13+ 做 wheel 探测。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.force_run

_INSTALL = Path(__file__).resolve().parents[1] / "install.py"


def _load_install():
    spec = importlib.util.spec_from_file_location("resolve_deps_install", _INSTALL)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_should_probe_wheels_only_from_313(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_install()

    monkeypatch.setattr(mod.sys, "version_info", (3, 11, 9, "final", 0))
    assert mod._should_probe_wheels() is False

    monkeypatch.setattr(mod.sys, "version_info", (3, 12, 7, "final", 0))
    assert mod._should_probe_wheels() is False

    monkeypatch.setattr(mod.sys, "version_info", (3, 13, 0, "final", 0))
    assert mod._should_probe_wheels() is True


def test_abort_skips_probe_on_311(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_install()
    monkeypatch.setattr(mod.sys, "version_info", (3, 11, 9, "final", 0))

    called = []

    def boom(*_a, **_k):
        called.append(1)
        return 1

    monkeypatch.setattr(mod.Utils.pkg, "run_pip", boom)
    req = tmp_path / "requirements.txt"
    req.write_text("numpy==2.4.6\npandas==2.2.0\nduckdb==1.5.6\n", encoding="utf-8")
    assert mod._abort_if_wheels_missing(req) is None
    assert called == []
