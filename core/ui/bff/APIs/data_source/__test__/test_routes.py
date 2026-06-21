"""BFF data source routes smoke tests."""

from __future__ import annotations

import pytest

from core.ui.bff.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_data_sources_list_ok(client):
    rv = client.get("/api/v1/data-sources/list?page=1&limit=10")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["status"] == "ok"
    assert "items" in body["message"]
    assert "total" in body["message"]
    if body["message"]["items"]:
        row = body["message"]["items"][0]
        assert "name" in row
        assert "display_name" in row
        assert "providers" in row
        assert "renew_type" in row
        assert "renew_type_label" in row
        assert "renew_interval_days" in row
        assert "rate_limit_per_minute" in row
        assert "requires_auth" in row
        assert "auth_ready" in row
        assert "can_renew" in row
        assert "update_status" not in row
        assert "origin" in row
        assert "is_custom" in row
        assert "data_end" in body["message"]


def test_data_sources_freshness_ok(client):
    rv = client.get("/api/v1/data-sources/freshness")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["status"] == "ok"
    assert "items" in body["message"]
    assert isinstance(body["message"]["items"], dict)
    assert "data_end" in body["message"]
