"""Local prefs + soft-prompt frequency state for feedback."""

from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..defaults import FeedbackDefaults

logger = logging.getLogger(__name__)


class FeedbackPrefsService:
    """
    Persist prompt opt-out and frequency counters.

    - Hard opt-out: ``userspace/system/config/feedback_prefs.json``
    - Soft counters: ``userspace/.ntq/feedback/prompt_state.json``
    """

    @staticmethod
    def get_prefs() -> Dict[str, Any]:
        raw = FeedbackPrefsService._read_json(FeedbackPrefsService._prefs_path()) or {}
        return {
            "prompts_disabled": bool(raw.get("prompts_disabled")),
            "decided_at": str(raw.get("decided_at") or ""),
            "source": str(raw.get("source") or ""),
        }

    @staticmethod
    def set_prompts_disabled(disabled: bool, *, source: str = "settings_ui") -> bool:
        try:
            path = FeedbackPrefsService._prefs_path()
            if path is None:
                return False
            payload = {
                "prompts_disabled": bool(disabled),
                "decided_at": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "source": str(source or "")[:32],
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return True
        except Exception as exc:
            logger.debug("feedback prefs write failed: %s", exc)
            return False

    @staticmethod
    def note_task_success(*, source: str = "") -> Dict[str, Any]:
        """
        Record one successful task; decide whether to show soft prompt.

        Never raises. Return shape always includes ``should_prompt``.
        """
        try:
            prefs = FeedbackPrefsService.get_prefs()
            if prefs.get("prompts_disabled"):
                return {"should_prompt": False, "reason": "disabled"}

            state = FeedbackPrefsService._load_state()
            state["success_count"] = int(state.get("success_count") or 0) + 1
            state["last_success_at"] = time.time()
            state["last_success_source"] = str(source or "")[:32]
            FeedbackPrefsService._save_state(state)

            min_ok = FeedbackDefaults.MIN_SUCCESS_BEFORE_PROMPT
            if int(state["success_count"]) < min_ok:
                return {
                    "should_prompt": False,
                    "reason": "need_more_success",
                    "success_count": state["success_count"],
                }

            last_prompt = float(state.get("last_prompt_at") or 0)
            cooldown = float(FeedbackDefaults.PROMPT_COOLDOWN_SEC)
            if last_prompt and (time.time() - last_prompt) < cooldown:
                return {"should_prompt": False, "reason": "cooldown"}

            if random.random() > float(FeedbackDefaults.PROMPT_PROBABILITY):
                return {"should_prompt": False, "reason": "probability"}

            state["last_prompt_at"] = time.time()
            state["prompt_count"] = int(state.get("prompt_count") or 0) + 1
            FeedbackPrefsService._save_state(state)
            return {
                "should_prompt": True,
                "reason": "eligible",
                "success_count": state["success_count"],
            }
        except Exception as exc:
            logger.debug("note_task_success failed: %s", exc)
            return {"should_prompt": False, "reason": "error"}

    @staticmethod
    def snooze_prompt() -> bool:
        """Mark prompt dismissed for this cooldown window (already stamped on show)."""
        try:
            state = FeedbackPrefsService._load_state()
            state["last_prompt_at"] = time.time()
            state["last_action"] = "snooze"
            FeedbackPrefsService._save_state(state)
            return True
        except Exception:
            return False

    @staticmethod
    def disable_prompts(*, source: str = "popup") -> bool:
        return FeedbackPrefsService.set_prompts_disabled(True, source=source)

    @staticmethod
    def _prefs_path() -> Optional[Path]:
        try:
            from core.infra.project_context import ProjectContext

            return ProjectContext.path.get_user_config_root() / "feedback_prefs.json"
        except Exception as exc:
            logger.debug("feedback prefs path unavailable: %s", exc)
            return None

    @staticmethod
    def _state_path() -> Optional[Path]:
        try:
            from core.infra.project_context import ProjectContext

            root = ProjectContext.path.get_userspace_ntq_directory() / "feedback"
            root.mkdir(parents=True, exist_ok=True)
            return root / "prompt_state.json"
        except Exception as exc:
            logger.debug("feedback state path unavailable: %s", exc)
            return None

    @staticmethod
    def _load_state() -> Dict[str, Any]:
        raw = FeedbackPrefsService._read_json(FeedbackPrefsService._state_path())
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _save_state(state: Dict[str, Any]) -> None:
        path = FeedbackPrefsService._state_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _read_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
        if path is None or not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else None
        except Exception:
            return None
