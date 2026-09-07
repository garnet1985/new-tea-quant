"""Tests for BFF shared client_log / response helpers."""

from __future__ import annotations

import logging

import pytest

from core.bff.shared.client_log import log_degraded
from core.bff.shared.response import from_payload, ok


def test_log_degraded_emits_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="bff.client"):
        log_degraded("test.scope", ValueError("boom"), "extra")
    assert any("test.scope" in r.message for r in caplog.records)
    assert any("boom" in r.message or "extra" in r.message for r in caplog.records)


def test_from_payload_ok_passthrough(app):
    with app.app_context():
        resp, status = from_payload({"status": "ok", "message": {"x": 1}})
        assert status == 200
        assert resp.get_json()["status"] == "ok"


def test_from_payload_error_maps_to_http_error(app):
    with app.app_context():
        resp, status = from_payload(
            {
                "status": "error",
                "message": {"detail": "步骤不存在", "code": "SETUP_STEP_NOT_FOUND"},
            },
            error_http_status=400,
        )
        assert status == 400
        body = resp.get_json()
        assert body["status"] == "error"
        assert body["message"]["detail"] == "步骤不存在"
        assert body["message"]["code"] == "SETUP_STEP_NOT_FOUND"


def test_error_helper_merges_extra(app):
    from core.bff.shared.response import error

    with app.app_context():
        resp, status = error(
            "settings.py 已在别处更新",
            409,
            code="settings_conflict",
            extra={"settings_rev": "abc", "disk_settings": {"n": 1}},
        )
        assert status == 409
        body = resp.get_json()
        assert body["message"]["code"] == "settings_conflict"
        assert body["message"]["settings_rev"] == "abc"
        assert body["message"]["disk_settings"] == {"n": 1}


@pytest.fixture
def app():
    from core.bff.app import create_app

    return create_app()
