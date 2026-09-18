"""Global helper 关闭账本：坏文件、幂等覆盖、未知 helpId。"""

from __future__ import annotations

import json

import pytest

from core.bff.APIs.platform.app_settings import ui_helper

pytestmark = pytest.mark.force_run


@pytest.fixture
def ledger_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ui_helper,
        "_ledger_path",
        lambda: tmp_path / ui_helper.UI_HELPER_FILENAME,
    )
    return tmp_path


def _write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_missing_file_is_empty(ledger_dir):
    assert ui_helper.get_ui_helper() == {"dismissed": {}}


def test_corrupt_json_is_empty(ledger_dir):
    (ledger_dir / "ui_helper.json").write_text("{not-json", encoding="utf-8")
    assert ui_helper.get_ui_helper() == {"dismissed": {}}


def test_non_object_json_is_empty(ledger_dir):
    (ledger_dir / "ui_helper.json").write_text("[]", encoding="utf-8")
    assert ui_helper.get_ui_helper() == {"dismissed": {}}


def test_unknown_help_id_is_kept(ledger_dir):
    _write(
        ledger_dir / "ui_helper.json",
        {
            "dismissed": {
                "future-complex-page": {
                    "version": 2,
                    "at": "2026-09-18T00:00:00Z",
                    "source": "skip",
                },
            },
        },
    )
    out = ui_helper.get_ui_helper()
    assert "future-complex-page" in out["dismissed"]
    assert out["dismissed"]["future-complex-page"]["version"] == 2
    assert out["dismissed"]["future-complex-page"]["source"] == "skip"


def test_save_unknown_help_id(ledger_dir):
    body, err = ui_helper.save_ui_helper(
        {"helpId": "not-in-catalog", "version": 1, "source": "ack"},
    )
    assert err is None
    assert "not-in-catalog" in body["dismissed"]
    stored = json.loads((ledger_dir / "ui_helper.json").read_text(encoding="utf-8"))
    assert stored["dismissed"]["not-in-catalog"]["source"] == "ack"


def test_save_is_idempotent_and_preserves_others(ledger_dir):
    ui_helper.save_ui_helper(
        {"helpId": "strategy-design", "version": 1, "source": "ack"},
    )
    ui_helper.save_ui_helper(
        {"helpId": "scan", "version": 1, "source": "skip"},
    )
    body, err = ui_helper.save_ui_helper(
        {"helpId": "strategy-design", "version": 3, "source": "skip"},
    )
    assert err is None
    dismissed = body["dismissed"]
    assert set(dismissed) == {"strategy-design", "scan"}
    assert dismissed["scan"]["source"] == "skip"
    assert dismissed["strategy-design"]["version"] == 3
    assert dismissed["strategy-design"]["source"] == "skip"
    assert dismissed["strategy-design"]["at"]


def test_save_rejects_bad_payload(ledger_dir):
    _, err = ui_helper.save_ui_helper({"version": 1, "source": "ack"})
    assert err == "缺少 helpId"
    _, err = ui_helper.save_ui_helper(
        {"helpId": "../etc", "version": 1, "source": "ack"},
    )
    assert "helpId" in err
    _, err = ui_helper.save_ui_helper({"helpId": "strategy-design", "source": "ack"})
    assert err == "缺少 version"
    _, err = ui_helper.save_ui_helper(
        {"helpId": "strategy-design", "version": 0, "source": "ack"},
    )
    assert err == "version 须为正整数"
    _, err = ui_helper.save_ui_helper(
        {"helpId": "strategy-design", "version": 1, "source": "later"},
    )
    assert err == "source 须为 ack 或 skip"


def test_skips_corrupt_entries_keeps_valid(ledger_dir):
    _write(
        ledger_dir / "ui_helper.json",
        {
            "dismissed": {
                "strategy-design": {"version": 1, "at": "2026-01-01T00:00:00Z", "source": "ack"},
                "bad-shape": "nope",
                "no-version": {"source": "ack"},
            },
        },
    )
    out = ui_helper.get_ui_helper()
    assert set(out["dismissed"]) == {"strategy-design"}


def test_http_get_post_roundtrip(ledger_dir):
    from core.bff.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        empty = client.get("/api/v1/settings/ui-helper")
        assert empty.status_code == 200
        assert empty.get_json()["message"] == {"dismissed": {}}

        posted = client.post(
            "/api/v1/settings/ui-helper",
            json={"helpId": "strategy-design", "version": 1, "source": "ack"},
        )
        assert posted.status_code == 200
        body = posted.get_json()
        assert body["status"] == "ok"
        assert body["message"]["dismissed"]["strategy-design"]["version"] == 1

        again = client.get("/api/v1/settings/ui-helper")
        assert again.get_json()["message"]["dismissed"]["strategy-design"]["source"] == "ack"
