"""updater 远端 zip URL 与下载辅助。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_HELPER = _REPO / "setup" / "updater" / "helper.py"


def _load_helper():
    upd = str(_HELPER.parent)
    if upd not in sys.path:
        sys.path.insert(0, upd)
    name = "ntq_updater_helper_test"
    spec = importlib.util.spec_from_file_location(name, _HELPER)
    if spec is None or spec.loader is None:
        raise ImportError(_HELPER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_gitee_archive_url_uses_api_zipball_not_github_style():
    h = _load_helper()
    urls = h.archive_zip_candidate_urls("https://gitee.com/garnet/new-tea-quant", "master")
    assert len(urls) == 1
    assert urls[0] == (
        "https://gitee.com/api/v5/repos/garnet/new-tea-quant/zipball?ref=master"
    )
    assert "/archive/master.zip" not in urls[0]
    assert "/repository/archive/" not in urls[0]


def test_gitee_archive_url_includes_token_when_set(monkeypatch):
    h = _load_helper()
    monkeypatch.setenv("NTQ_GITEE_ACCESS_TOKEN", "tok123")
    urls = h.archive_zip_candidate_urls("https://gitee.com/garnet/new-tea-quant", "master")
    assert "access_token=tok123" in urls[0]


def test_github_archive_url():
    h = _load_helper()
    urls = h.archive_zip_candidate_urls(
        "https://github.com/garnet1985/new-tea-quant", "master"
    )
    assert urls == [
        "https://github.com/garnet1985/new-tea-quant/archive/refs/heads/master.zip"
    ]
