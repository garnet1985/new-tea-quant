"""安装演示包：URL 与下载（不联网）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.ntq_external import install_demo
from core.modules.ntq_external.conf import site_target

pytestmark = pytest.mark.force_run


def test_install_demo_urls_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "core.infra.project_context.core.path_manager.PathManager.get_user_config_root",
        staticmethod(lambda: tmp_path),
    )
    assert site_target.install_demo_url().endswith("/api/v1/ntq-data/install/demo")
    assert site_target.install_demo_meta_url().endswith("/api/v1/ntq-data/install/demo/meta")
    assert install_demo.resolve_install_demo_url() == site_target.install_demo_url()


def test_install_demo_url_env_override(monkeypatch) -> None:
    monkeypatch.setenv("NTQ_INSTALL_DEMO_URL", "http://127.0.0.1:8080/demo.zip")
    assert install_demo.resolve_install_demo_url() == "http://127.0.0.1:8080/demo.zip"


def test_download_install_demo_skips_when_present(tmp_path: Path, monkeypatch) -> None:
    zip_path = tmp_path / "data_demo.zip"
    zip_path.write_bytes(b"PK\x03\x04existing")

    def _boom(*_a, **_k):
        raise AssertionError("should not download")

    monkeypatch.setattr(install_demo, "_http_get_bytes", _boom)
    out = install_demo.download_install_demo(tmp_path, force=False)
    assert out == zip_path
    assert zip_path.read_bytes() == b"PK\x03\x04existing"


def test_download_install_demo_writes_and_checks_sha(tmp_path: Path, monkeypatch) -> None:
    payload = b"PK\x03\x04demo-bytes"
    import hashlib

    digest = hashlib.sha256(payload).hexdigest()
    meta = {"sha256": digest, "stock_count": 300}

    def _fake_get(url: str, *, timeout_sec: float = 30.0) -> bytes:
        if url.endswith("/meta") or "demo/meta" in url:
            return json.dumps(meta).encode("utf-8")
        return payload

    monkeypatch.setattr(install_demo, "_http_get_bytes", _fake_get)
    monkeypatch.setattr(
        install_demo,
        "resolve_install_demo_url",
        lambda: "http://example.test/api/v1/ntq-data/install/demo",
    )
    monkeypatch.setattr(
        install_demo,
        "resolve_install_demo_meta_url",
        lambda: "http://example.test/api/v1/ntq-data/install/demo/meta",
    )

    out = install_demo.download_install_demo(tmp_path, force=True)
    assert out.is_file()
    assert out.read_bytes() == payload
    meta_path = tmp_path / "data_demo.meta.json"
    assert meta_path.is_file()
    assert json.loads(meta_path.read_text(encoding="utf-8"))["sha256"] == digest
