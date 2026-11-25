"""会员分卷下载：齐套跳过、校验失败。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from core.infra.membership import Membership
from core.infra.project_context.core.path_manager import PathManager
from core.modules.ntq_external import install_member

pytestmark = pytest.mark.force_run

TOKEN = "ntq_" + "cd" * 24


@pytest.fixture
def token_file(tmp_path: Path, monkeypatch):
    path = tmp_path / "membership_token.txt"
    path.write_text(TOKEN + "\n", encoding="utf-8")
    monkeypatch.setattr(
        PathManager,
        "get_membership_token_file",
        staticmethod(lambda: path),
    )
    return path


def _meta_two_parts(payload_a: bytes, payload_b: bytes) -> dict:
    return {
        "kind": "member_data_parts",
        "parts": [
            {
                "file": "data_member_3y_part01.zip",
                "index": 1,
                "size_bytes": len(payload_a),
                "sha256": hashlib.sha256(payload_a).hexdigest(),
            },
            {
                "file": "data_member_3y_part02.zip",
                "index": 2,
                "size_bytes": len(payload_b),
                "sha256": hashlib.sha256(payload_b).hexdigest(),
            },
        ],
    }


def test_member_parts_complete_and_skip_download(tmp_path: Path, token_file, monkeypatch):
    a = b"PK\x03\x04aaaa"
    b = b"PK\x03\x04bbbb"
    meta = _meta_two_parts(a, b)
    dest = tmp_path / "member"
    dest.mkdir()
    (dest / install_member.MEMBER_MANIFEST_NAME).write_text(
        json.dumps(meta), encoding="utf-8"
    )
    (dest / "data_member_3y_part01.zip").write_bytes(a)
    (dest / "data_member_3y_part02.zip").write_bytes(b)
    assert install_member.member_parts_complete(dest, meta) is True

    def _boom(*_a, **_k):
        raise AssertionError("should not download")

    monkeypatch.setattr(install_member, "_http_get_bytes", _boom)
    monkeypatch.setattr(install_member, "fetch_install_member_meta", lambda **_k: meta)
    out = install_member.download_install_member(dest, force=False)
    assert out == dest


def test_download_writes_parts(tmp_path: Path, token_file, monkeypatch):
    a = b"PK\x03\x04aaaa"
    b = b"PK\x03\x04bbbb"
    meta = _meta_two_parts(a, b)
    payloads = {
        1: a,
        2: b,
    }

    def _fake_get(url, **_kwargs):
        if url.endswith("/meta") or "meta" in url:
            return json.dumps(meta).encode("utf-8")
        for index, body in payloads.items():
            if url.rstrip("/").endswith(f"/{index}") or f"part/{index}" in url:
                return body
        raise install_member.InstallMemberError(f"unexpected url {url}")

    monkeypatch.setattr(install_member, "_http_get_bytes", _fake_get)
    monkeypatch.setattr(
        install_member,
        "resolve_install_member_meta_url",
        lambda: "http://example.test/meta",
    )
    monkeypatch.setattr(
        install_member,
        "resolve_install_member_part_url",
        lambda n: f"http://example.test/part/{n}",
    )
    dest = tmp_path / "member"
    out = install_member.download_install_member(dest, force=True)
    assert out == dest
    assert (dest / "data_member_3y_part01.zip").read_bytes() == a
    assert (dest / "data_member_3y_part02.zip").read_bytes() == b
    assert Membership.read() == TOKEN
