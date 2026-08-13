"""Feedback module unit tests (no real HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def feedback_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_root = tmp_path / "config"
    ntq_root = tmp_path / ".ntq"
    config_root.mkdir()
    ntq_root.mkdir()

    class _PathNS:
        @staticmethod
        def get_user_config_root():
            return config_root

        @staticmethod
        def get_userspace_ntq_directory():
            return ntq_root

    class _MetaNS:
        @staticmethod
        def core_version():
            return "0.0.test"

    class _PC:
        path = _PathNS()
        meta = _MetaNS()

    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext",
        _PC,
        raising=False,
    )
    # Prefs/submit import ProjectContext late; also patch where used.
    import core.infra.feedback.core.services.prefs_service as prefs_mod
    import core.infra.feedback.core.services.submit_service as submit_mod

    monkeypatch.setattr(
        prefs_mod,
        "FeedbackPrefsService",
        prefs_mod.FeedbackPrefsService,
    )

    def _fake_project_context_import():
        return _PC

    monkeypatch.setattr(
        "core.infra.feedback.core.services.prefs_service.FeedbackPrefsService._prefs_path",
        staticmethod(lambda: config_root / "feedback_prefs.json"),
    )
    monkeypatch.setattr(
        "core.infra.feedback.core.services.prefs_service.FeedbackPrefsService._state_path",
        staticmethod(lambda: (ntq_root / "feedback" / "prompt_state.json")),
    )
    (ntq_root / "feedback").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        submit_mod.FeedbackSubmitService,
        "_installation_id",
        staticmethod(lambda: "ntq_i_" + ("a" * 32)),
    )
    monkeypatch.setattr(
        submit_mod.FeedbackSubmitService,
        "_build_meta",
        staticmethod(lambda extra=None: {"ntq_version": "0.0.test"}),
    )

    posted = []

    def _post(url, payload, *, timeout_sec):
        posted.append({"url": url, "payload": payload, "timeout_sec": timeout_sec})
        return True

    monkeypatch.setattr(
        "core.infra.feedback.core.services.client_service.FeedbackClientService.post",
        staticmethod(_post),
    )
    return {"posted": posted, "config_root": config_root, "ntq_root": ntq_root}


def test_submit_bypasses_consent_and_posts(feedback_paths):
    from core.infra.feedback import Feedback

    ok = Feedback.submit(rating="up", text="nice", source="popup")
    assert ok is True
    assert len(feedback_paths["posted"]) == 1
    wire = feedback_paths["posted"][0]["payload"]
    assert wire["rating"] == "up"
    assert wire["text"] == "nice"
    assert wire["installation_id"].startswith("ntq_i_")
    assert "event_id" in wire


def test_submit_rejects_bad_rating(feedback_paths):
    from core.infra.feedback import Feedback

    assert Feedback.submit(rating="meh") is False
    assert feedback_paths["posted"] == []


def test_prompt_requires_three_successes(feedback_paths, monkeypatch):
    from core.infra.feedback import Feedback
    from core.infra.feedback.core.defaults import FeedbackDefaults

    monkeypatch.setattr(FeedbackDefaults, "PROMPT_PROBABILITY", 1.0)

    r1 = Feedback.note_task_success(source="scan")
    r2 = Feedback.note_task_success(source="scan")
    assert r1["should_prompt"] is False
    assert r2["should_prompt"] is False
    r3 = Feedback.note_task_success(source="scan")
    assert r3["should_prompt"] is True


def test_disable_prompts_blocks_future(feedback_paths, monkeypatch):
    from core.infra.feedback import Feedback
    from core.infra.feedback.core.defaults import FeedbackDefaults

    monkeypatch.setattr(FeedbackDefaults, "PROMPT_PROBABILITY", 1.0)
    Feedback.disable_prompts(source="popup")
    for _ in range(5):
        assert Feedback.note_task_success(source="scan")["should_prompt"] is False
    prefs = Feedback.get_prefs()
    assert prefs["prompts_disabled"] is True
    path = feedback_paths["config_root"] / "feedback_prefs.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["prompts_disabled"] is True
