"""反馈的本地默认。上报地址在 ``ntq_external.conf``。

可用环境变量 ``NTQ_FEEDBACK_ENDPOINT`` / ``NTQ_FEEDBACK_TIMEOUT`` 覆盖。
"""

from __future__ import annotations

from typing import Any, Dict


class FeedbackDefaults:
    """频控和体积。地址不在这里。"""

    TIMEOUT_SEC: float = 3.0
    MAX_TEXT_CODEPOINTS: int = 2000
    BODY_MAX_BYTES: int = 8192

    # Soft prompt frequency. Closing prompts is settings-only.
    # At most one prompt per local half-day: 00:00–12:00 and 12:00–24:00.
    MIN_SUCCESS_BEFORE_PROMPT: int = 1
    PROMPT_PROBABILITY: float = 1.0

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        from core.modules.ntq_external.conf.site_target import contact_url, feedback_url

        return {
            "target_url": feedback_url(),
            "timeout_sec": cls.TIMEOUT_SEC,
            "max_text_codepoints": cls.MAX_TEXT_CODEPOINTS,
            "body_max_bytes": cls.BODY_MAX_BYTES,
            "min_success_before_prompt": cls.MIN_SUCCESS_BEFORE_PROMPT,
            "prompt_probability": cls.PROMPT_PROBABILITY,
            "contact_url": contact_url(),
        }


__all__ = ["FeedbackDefaults"]
