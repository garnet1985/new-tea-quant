"""公开 Facade 冒烟（不联网）。"""

from __future__ import annotations

import pytest

import core.modules.ntq_external as pkg
from core.modules.ntq_external import register_trace_endpoint, site_urls
from core.modules.ntq_external.feedback import Feedback

pytestmark = pytest.mark.force_run


def test_root_exports() -> None:
    assert pkg.__all__ == ["register_trace_endpoint", "site_urls"]
    assert callable(register_trace_endpoint)
    assert callable(site_urls)


def test_site_urls_shape() -> None:
    urls = site_urls()
    for key in ("disclaimer_url", "license_url", "contact_url", "register_url"):
        assert isinstance(urls[key], str)
        assert urls[key].startswith("http")
    docs = urls["docs"]
    assert set(docs) == {"strategy", "opportunities", "tag", "datasource", "contract"}
    for value in docs.values():
        assert value.startswith("http")


def test_register_trace_endpoint() -> None:
    assert register_trace_endpoint() is None


def test_feedback_surface() -> None:
    for name in (
        "submit",
        "note_task_success",
        "snooze_prompt",
        "disable_prompts",
        "get_prefs",
        "set_prompts_disabled",
        "contact_url",
    ):
        assert callable(getattr(Feedback, name)), name
