"""BFF tag routes smoke tests."""

from __future__ import annotations

import pytest

from core.ui.bff.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_runtime_pipeline_idle(client):
    rv = client.get("/api/v1/runtime/pipeline")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["status"] == "ok"
    assert body["message"]["busy"] is False


def test_tags_list_ok(client):
    rv = client.get("/api/v1/tags/list?page=1&limit=10")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["status"] == "ok"
    assert "items" in body["message"]
    assert "total" in body["message"]
