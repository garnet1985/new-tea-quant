"""Feedback facade — soft in-app feedback (no Trace.consent)."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .core.defaults import FeedbackDefaults
from .core.services.prefs_service import FeedbackPrefsService
from .core.services.submit_service import FeedbackSubmitService


class Feedback:
    """
    Soft feedback facade.

    All APIs are static. Submitting feedback does **not** require Trace consent;
    users may only disable the *prompt*. Failures never affect callers.
    """

    Defaults = FeedbackDefaults

    @staticmethod
    def submit(
        *,
        rating: str,
        text: str = "",
        source: str = "popup",
        meta: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        """POST one feedback event; returns whether the HTTP ingest succeeded."""
        return FeedbackSubmitService.submit(
            rating=rating, text=text, source=source, meta=meta
        )

    @staticmethod
    def note_task_success(*, source: str = "") -> Dict[str, Any]:
        """Record a successful task; may return ``should_prompt=True``."""
        return FeedbackPrefsService.note_task_success(source=source)

    @staticmethod
    def snooze_prompt() -> bool:
        """User dismissed the soft prompt for now."""
        return FeedbackPrefsService.snooze_prompt()

    @staticmethod
    def disable_prompts(*, source: str = "popup") -> bool:
        """Never show soft prompts again (user can re-enable in settings)."""
        return FeedbackPrefsService.disable_prompts(source=source)

    @staticmethod
    def get_prefs() -> Dict[str, Any]:
        return FeedbackPrefsService.get_prefs()

    @staticmethod
    def set_prompts_disabled(disabled: bool, *, source: str = "settings_ui") -> bool:
        return FeedbackPrefsService.set_prompts_disabled(disabled, source=source)

    @staticmethod
    def contact_url() -> str:
        return str(FeedbackDefaults.CONTACT_URL)


__all__ = ["Feedback"]
