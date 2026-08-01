"""BFF data contract routes smoke tests."""

from __future__ import annotations

import pytest

from core.bff.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_data_contracts_list_ok(client):
    rv = client.get("/api/v1/data-contracts/list?page=1&limit=10")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["status"] == "ok"
    assert "items" in body["message"]
    assert "total" in body["message"]
    if body["message"]["items"]:
        row = body["message"]["items"][0]
        assert "key" in row
        assert "display_name" in row
        assert "is_time_series" in row
        assert "is_per_entity" in row
        assert "origin" in row
        assert "is_custom" in row
