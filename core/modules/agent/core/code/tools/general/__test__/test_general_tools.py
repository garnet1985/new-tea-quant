"""通用工具：calculator / files / web_search（无网络）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.tools.general.calculator_tool import calculator
from core.modules.agent.core.code.tools.general.fs_tools import (
    list_dir,
    read_file,
    search_files,
)
from core.modules.agent.core.code.tools.general.python_snippet_tool import (
    run_python_snippet,
)
from core.modules.agent.core.code.tools.general.web_search_tool import web_search
from core.modules.agent.core.code.tools.general.wiki_search_tool import search_wiki
import core.modules.agent.core.code.tools.general.web_search_tool as web_search_mod
import core.modules.agent.core.code.tools.general.read_url_tool as read_url_mod
import core.modules.agent.core.code.tools.general.trading_calendar_tool as cal_mod
from core.modules.agent.core.code.tools.general.read_url_tool import read_url
from core.modules.agent.core.code.tools.general.trading_calendar_tool import (
    trading_calendar,
)


def test_calculator_basic() -> None:
    out = calculator({"expression": "(1+0.1)**2 - 1"})
    assert out.get("ok") is True, out
    assert abs(float(out["result"]) - 0.21) < 1e-9


def test_calculator_rejects_names() -> None:
    out = calculator({"expression": "__import__('os').system('x')"})
    assert out.get("ok") is False


@pytest.fixture()
def userspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "userspace"
    strat = root / "strategies" / "demo_s"
    strat.mkdir(parents=True)
    (strat / "settings.py").write_text(
        'settings = {"meta": {"key": "demo_s"}, "is_enabled": True}\n',
        encoding="utf-8",
    )
    (strat / "strategy.py").write_text(
        "def is_opportunity(self, ctx, records):\n    return False\n",
        encoding="utf-8",
    )
    ext = root / "extensions" / "tables"
    ext.mkdir(parents=True)
    secrets = root / "extensions" / "llm_providers" / "deepseek"
    secrets.mkdir(parents=True)
    (secrets / "api_key.txt").write_text("secret\n", encoding="utf-8")
    (root / "system").mkdir()
    (root / "system" / "membership.json").write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_userspace_root",
        lambda: root,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_strategies_root",
        lambda: root / "strategies",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_extensions_root",
        lambda: root / "extensions",
    )
    return root


def test_list_search_read(userspace: Path) -> None:
    listed = list_dir({"path": "strategies"})
    assert listed.get("ok") is True, listed
    assert any(e["name"] == "demo_s" for e in listed.get("entries") or [])

    found = search_files({"query": "is_opportunity", "path": "strategies"})
    assert found.get("ok") is True, found
    assert found.get("count", 0) >= 1

    read = read_file({"path": "strategies/demo_s/settings.py"})
    assert read.get("ok") is True, read
    assert "demo_s" in str(read.get("content") or "")


def test_read_denies_secrets(userspace: Path) -> None:
    deny_key = read_file({"path": "extensions/llm_providers/deepseek/api_key.txt"})
    assert deny_key.get("ok") is False
    deny_sys = read_file({"path": "system/membership.json"})
    assert deny_sys.get("ok") is False


def test_web_search_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        web_search_mod, "_via_member_knowledge_brief", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        web_search_mod.AiChannel, "load_api_key", staticmethod(lambda _pid: None)
    )
    out = web_search({"query": "美联储 利率"})
    assert out.get("ok") is False
    err = str(out.get("error") or "")
    assert "会员" in err or "API Key" in err


def test_web_search_prefers_member(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        web_search_mod,
        "_via_member_knowledge_brief",
        lambda q, c: {
            "ok": True,
            "via": "ntq",
            "query": q,
            "brief": "简报",
            "count": 0,
            "results": [],
            "note": "x",
        },
    )
    out = web_search({"query": "美联储"})
    assert out.get("ok") is True
    assert out.get("via") == "ntq"
    assert out.get("brief") == "简报"


def test_web_search_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return (
                b'{"results":[{"title":"T","url":"https://ex.com","snippet":"s",'
                b'"summary":"sum","site_name":"Ex","date":null,'
                b'"authority":3,"rerank_score":2.0}]}'
            )

    monkeypatch.setattr(
        web_search_mod, "_via_member_knowledge_brief", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        web_search_mod.AiChannel, "load_api_key", staticmethod(lambda _pid: "sk-test")
    )
    monkeypatch.setattr(
        web_search_mod.urllib.request, "urlopen", lambda *a, **k: _Resp()
    )
    out = web_search({"query": "美联储", "count": 3})
    assert out.get("ok") is True, out
    assert out.get("via") == "local_deepseek"
    assert out.get("count") == 1
    assert out["results"][0]["title"] == "T"


def test_search_wiki_finds_known_doc() -> None:
    out = search_wiki({"query": "stock_list_filter"})
    assert out.get("ok") is True, out
    assert out.get("count", 0) >= 1


def test_read_url_rejects_bad_scheme() -> None:
    out = read_url({"url": "file:///etc/passwd"})
    assert out.get("ok") is False


def test_read_url_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"title":"Hi","content":"# hello\\nworld"}'

    monkeypatch.setattr(
        read_url_mod.AiChannel, "load_api_key", staticmethod(lambda _pid: "sk-test")
    )
    monkeypatch.setattr(
        read_url_mod.urllib.request, "urlopen", lambda *a, **k: _Resp()
    )
    out = read_url({"url": "https://example.com/a"})
    assert out.get("ok") is True, out
    assert out.get("title") == "Hi"
    assert "hello" in str(out.get("content") or "")


def test_trading_calendar_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Cal:
        def load_open_dates(self, start, end, *, market="SSE"):
            if start == end == "20240102":
                return ["20240102"]
            if start <= "20240102" <= end:
                return ["20240102"]
            if end < "20240102":
                return ["20231229"]
            return []

        def get_next_trading_date(self, date, *, market="SSE"):
            assert date == "20240102"
            return "20240103"

        def get_latest_completed_trading_date(self, *, as_of_date=None):
            return "20240102"

    class _DM:
        calendar = _Cal()

    monkeypatch.setattr(cal_mod, "DataManager", lambda: _DM())
    out = trading_calendar({"date": "20240102"})
    assert out.get("ok") is True, out
    assert out.get("is_open") is True
    assert out.get("next_open") == "20240103"
    assert out.get("prev_open") == "20231229"
    assert out.get("latest_completed") == "20240102"


def test_trading_calendar_range(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Cal:
        def load_open_dates(self, start, end, *, market="SSE"):
            return ["20240102", "20240103"]

        def get_next_trading_date(self, *a, **k):
            raise AssertionError("unused")

        def get_latest_completed_trading_date(self, **k):
            raise AssertionError("unused")

    class _DM:
        calendar = _Cal()

    monkeypatch.setattr(cal_mod, "DataManager", lambda: _DM())
    out = trading_calendar({"start": "20240101", "end": "20240105"})
    assert out.get("ok") is True, out
    assert out.get("count") == 2
    assert out.get("open_dates") == ["20240102", "20240103"]


def test_run_python_snippet_stats() -> None:
    out = run_python_snippet(
        {
            "code": "xs=[1,2,3,4]\nresult=statistics.median(xs)",
        }
    )
    assert out.get("ok") is True, out
    assert out.get("result") == 2.5


def test_run_python_snippet_rejects_import() -> None:
    out = run_python_snippet({"code": "import os\nresult=1"})
    assert out.get("ok") is False
    assert "Import" in str(out.get("error") or "")


def test_run_python_snippet_rejects_dunder() -> None:
    out = run_python_snippet({"code": "result = ().__class__"})
    assert out.get("ok") is False
