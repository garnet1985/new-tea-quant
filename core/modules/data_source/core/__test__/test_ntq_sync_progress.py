"""官网同步会在翻页前打出进度，并且只拉这一张表的计划区间。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run


def test_pull_prints_the_page_it_is_waiting_on(capsys):
    from core.modules.data_source.core.progress import SyncProgress
    from core.modules.data_source.core.service import official_sync

    class _Provider:
        def __init__(self):
            self.calls = []

        def sync(self, table, start=None, end=None):
            self.calls.append((table, start, end))
            if len(self.calls) == 1:
                return {"rows": [{"date": "20230101"}], "next_start": "c.2", "total": 4}
            return {"rows": [{"date": "20230102"}], "next_start": None}

    class _Handler:
        def get_key(self):
            return "cpi"

        def __init__(self):
            self.progress = SyncProgress("cpi")
            self.context = {
                "providers": {"ntq": _Provider()},
                "is_dry_run": False,
            }

    handler = _Handler()
    official_sync._upsert = lambda handler, table, rows: None
    saved = official_sync._pull(handler, "sys_data_cpi", "20230101", "20251231")
    text = capsys.readouterr().out
    assert saved == 2
    assert handler.context["providers"]["ntq"].calls[0] == (
        "sys_data_cpi",
        "20230101",
        "20251231",
    )
    assert "正在读取第 1 页，已写入 0 行" in text
    assert "正在读取第 2 页，已写入 1 行，25%" in text


class _Job:
    def __init__(self, entity_id, start, end):
        self.start_date = start
        self.end_date = end
        self.apis = [type("Api", (), {"params": {"id": entity_id}})()]


class _EntityProvider:
    def __init__(self, plan):
        self.plan_result = plan
        self.synced = []
        self.asked = None

    def plan_entities(self, table, stocks, pack):
        self.asked = (table, stocks, pack)
        return self.plan_result

    def sync(self, table, start=None, end=None, entity_id=None):
        self.synced.append((entity_id, start, end))
        return {"rows": [{"id": entity_id, "date": start}], "next_start": None}


def _entity_handler(provider):
    from core.modules.data_source.core.progress import SyncProgress

    class _Config:
        def get_table_name(self):
            return "sys_data_stock_klines"

    handler = type("Handler", (), {})()
    handler.get_key = lambda: "stock_klines"
    handler.progress = SyncProgress("stock_klines")
    handler.context = {
        "providers": {"ntq": provider},
        "config": _Config(),
        "is_dry_run": False,
    }
    return handler


def test_entities_are_pulled_one_stock_at_a_time(capsys, monkeypatch):
    from core.modules.data_source.core.service import official_sync

    monkeypatch.setattr(official_sync, "_upsert", lambda handler, table, rows: None)
    provider = _EntityProvider({
        "files": [],
        "stocks": [
            {"id": "000001.SZ", "start": "20260101", "end": "20261014"},
            {"id": "000002.SZ", "start": "20260101", "end": "20261014"},
        ],
    })
    handler = _entity_handler(provider)
    jobs = [
        _Job("000001.SZ", "20260101", "20261014"),
        _Job("000002.SZ", "20260101", "20261014"),
    ]
    saved = official_sync.pull_entities(handler, jobs)
    text = capsys.readouterr().out
    assert saved == 2
    assert provider.synced == [
        ("000001.SZ", "20260101", "20261014"),
        ("000002.SZ", "20260101", "20261014"),
    ]
    assert "抓取 2/2，已写入 2 行" in text


def test_plan_imports_the_cache_and_keeps_the_early_stock(capsys, monkeypatch):
    from core.modules.data_source.core.service import official_sync

    monkeypatch.setattr(official_sync, "_import_snapshot", lambda handler, provider, table, path: 9)
    provider = _EntityProvider({
        "files": [{"path": "/api/recent.csv.gz", "from": "20260920", "through": "20261014"}],
        "stocks": [{"id": "000003.SZ", "start": "20100101", "end": "20260919"}],
    })
    handler = _entity_handler(provider)
    jobs = [
        _Job("000001.SZ", "20261001", "20261014"),
        _Job("000003.SZ", "20100101", "20261014"),
    ]
    saved = official_sync.pull_entities(handler, jobs)
    text = capsys.readouterr().out
    assert saved == 10
    assert "远端计划：1 个数据包（20260920–20261014），导入后再按股票补 1 只" in text
    assert "数据包 1/1 已导入 9 行，截止 20261014" in text
    assert provider.synced == [("000003.SZ", "20100101", "20260919")]
    assert provider.asked[1][0]["id"] == "000001.SZ"
    assert provider.asked[1][1]["start"] == "20100101"


def test_busy_slot_is_waited_out_past_a_handful_of_retries(monkeypatch):
    import io
    import json
    import urllib.error
    import urllib.request

    from userspace.extensions.data_source.providers.ntq.provider import NtqProvider

    calls = {"n": 0}

    def urlopen(request, timeout=None):
        calls["n"] += 1
        calls["timeout"] = timeout
        if calls["n"] <= 7:
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "busy",
                {"Retry-After": "2"},
                io.BytesIO(b"{}"),
            )
        body = json.dumps({
            "table": "sys_data_stock_klines",
            "id": "000001.SZ",
            "rows": [{"id": "000001.SZ"}],
        }).encode()
        response = io.BytesIO(body)
        response.status = 200
        response.headers = {}
        return response

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(
        "userspace.extensions.data_source.providers.ntq.provider.time.sleep",
        lambda pause: None,
    )
    provider = NtqProvider({"token": "t", "base_url": "https://example.test"})
    page = provider.sync("sys_data_stock_klines", entity_id="000001.SZ")
    assert page["rows"] == [{"id": "000001.SZ"}]
    assert calls["n"] == 8
    assert calls["timeout"] == 120.0


def test_blank_numbers_become_null():
    from core.modules.data_source.core.service import official_sync

    row = {
        "id": "002714.SZ",
        "date": "20240603",
        "pe": "",
        "dv_ttm": "1.515",
        "name": "",
    }
    official_sync._blank_as_null(
        {
            "fields": [
                {"name": "id", "type": "varchar"},
                {"name": "date", "type": "varchar"},
                {"name": "pe", "type": "float"},
                {"name": "dv_ttm", "type": "float"},
                {"name": "name", "type": "varchar"},
            ]
        },
        [row],
    )
    assert row["pe"] is None
    assert row["dv_ttm"] == "1.515"
    assert row["id"] == "002714.SZ"
    assert row["name"] == ""


def test_busy_wait_stops_when_the_slot_hold_is_over(monkeypatch):
    import io
    import urllib.error
    import urllib.request

    from core.modules.data_source.core.data_class.error import ProviderError
    from userspace.extensions.data_source.providers.ntq.provider import NtqProvider

    clock = {"t": 0.0}

    def urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url,
            429,
            "busy",
            {"Retry-After": "2"},
            io.BytesIO(b"{}"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(
        "userspace.extensions.data_source.providers.ntq.provider.time.monotonic",
        lambda: clock["t"],
    )
    monkeypatch.setattr(
        "userspace.extensions.data_source.providers.ntq.provider.time.sleep",
        lambda pause: clock.__setitem__("t", clock["t"] + pause),
    )
    provider = NtqProvider({"token": "t", "base_url": "https://example.test"})
    with pytest.raises(ProviderError):
        provider.sync("sys_data_stock_klines", entity_id="000001.SZ")
    assert clock["t"] == 120.0
