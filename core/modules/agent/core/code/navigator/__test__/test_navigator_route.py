"""Navigator：有序清单 + 金标评测。"""

from __future__ import annotations

from core.modules.agent.core.code.navigator.classifier import parse_kinds
from core.modules.agent.evaluate.gold_set import GOLD_CASES
from core.modules.agent.evaluate.harness import evaluate, format_report, worker_recall
from core.modules.agent.core.code.navigator.router import regex_route, route


def test_regex_pipeline_advice_then_worker():
    r = regex_route("推荐能赚钱的策略并帮我写一个")
    assert r.kind == "advice"
    assert r.queue == ("advice", "worker")


def test_regex_pipeline_identity_then_worker():
    r = regex_route("NTQ 是什么，顺便帮我回测一下")
    assert r.kind == "identity"
    assert r.queue == ("identity", "worker")


def test_regex_pipeline_oos_then_worker():
    r = regex_route("法国暴乱影响 A 股吗，帮我改止损并重跑回测")
    assert r.kind == "out_of_scope"
    assert r.queue == ("out_of_scope", "worker")


def test_regex_arch():
    assert regex_route("NTQ 的回测四步架构原理是什么？").kind == "guide_arch"


def test_parse_kinds_queue():
    assert parse_kinds('{"kinds":["advice","worker"]}') == ["advice", "worker"]
    assert parse_kinds('{"kinds":["guide"]}') == ["guide"]
    assert parse_kinds('{"kinds":["worker","advice"]}') == ["advice", "worker"]
    assert parse_kinds('{"kind":"guide"}') is None
    assert parse_kinds("nonsense") is None


def test_a0_regex_gold_floor():
    report = evaluate(
        name="A0_regex",
        router=lambda t: route(t, provider_id="ntq", mode="regex"),
    )
    assert report.total == len(GOLD_CASES)
    assert report.accuracy >= 0.90, format_report(report)
    assert report.queue_exact_rate >= 0.90, format_report(report)
    assert report.redline_miss == 0, format_report(report)
    assert report.false_worker == 0, format_report(report)
    assert worker_recall(report) >= 0.90, format_report(report)


def _install_oracle_classifier(monkeypatch):
    from core.modules.agent.core.code.navigator import classifier as clf
    from core.modules.agent.evaluate.gold_set import expected_kinds
    from core.infra.ai.contracts import CompleteResult
    import json

    by_text = {c["text"]: expected_kinds(c) for c in GOLD_CASES}

    def fake_complete(messages, **kwargs):
        user = messages[-1]["content"]
        kinds = by_text.get(user, ["guide"])
        return CompleteResult(
            reply=json.dumps({"kinds": kinds}, ensure_ascii=False),
            provider_id="ntq",
            model="stub",
        )

    monkeypatch.setattr(clf.AiChannel, "complete", staticmethod(fake_complete))


def test_route_uses_classifier_queue(monkeypatch):
    _install_oracle_classifier(monkeypatch)
    r = route("推荐能赚钱的策略并帮我写一个", provider_id="ntq")
    assert r.kind == "advice"
    assert r.queue == ("advice", "worker")


def test_escalate_advice_when_model_misses(monkeypatch):
    from core.modules.agent.core.code.navigator import classifier as clf
    from core.infra.ai.contracts import CompleteResult

    def fake_complete(messages, **kwargs):
        return CompleteResult(
            reply='{"kinds":["worker"]}', provider_id="ntq", model="stub"
        )

    monkeypatch.setattr(clf.AiChannel, "complete", staticmethod(fake_complete))
    r = route("推荐能赚钱的策略并帮我写一个", provider_id="ntq", mode="ask")
    assert r.kind == "advice"
    assert "advice" in r.queue


def test_a1_oracle(monkeypatch):
    _install_oracle_classifier(monkeypatch)
    report = evaluate(
        name="A1_oracle",
        router=lambda t: route(t, provider_id="ntq", mode="ask"),
    )
    assert report.accuracy >= 0.99, format_report(report)
    assert report.queue_exact_rate >= 0.99, format_report(report)


def test_classifier_failure_falls_back_to_regex(monkeypatch):
    from core.modules.agent.core.code.navigator import classifier as clf

    monkeypatch.setattr(clf, "classify_route", lambda *a, **k: None)
    assert (
        route("帮我改止损并重跑回测", provider_id="ntq", mode="ask").kind == "worker"
    )
