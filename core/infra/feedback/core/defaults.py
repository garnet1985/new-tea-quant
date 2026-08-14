"""Feedback 内置默认值（唯一源）。

上报地址改这里的 ``FeedbackDefaults.TARGET_URL``。
可用环境变量 ``NTQ_FEEDBACK_ENDPOINT`` / ``NTQ_FEEDBACK_TIMEOUT`` 覆盖。
"""

from __future__ import annotations

from typing import Any, Dict


class FeedbackDefaults:
    """内置默认；勿在别处再硬编码同一套数字 / URL。"""

    TARGET_URL: str = "https://www.new-tea.cn/api/v1/feedback"
    TIMEOUT_SEC: float = 3.0
    MAX_TEXT_CODEPOINTS: int = 2000
    BODY_MAX_BYTES: int = 8192

    # Soft prompt frequency
    MIN_SUCCESS_BEFORE_PROMPT: int = 3
    PROMPT_COOLDOWN_SEC: int = 2 * 24 * 3600
    PROMPT_PROBABILITY: float = 0.25

    CONTACT_URL: str = "https://new-tea.cn/zh-hans/contact?from=ntq_app"

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        return {
            "target_url": cls.TARGET_URL,
            "timeout_sec": cls.TIMEOUT_SEC,
            "max_text_codepoints": cls.MAX_TEXT_CODEPOINTS,
            "body_max_bytes": cls.BODY_MAX_BYTES,
            "min_success_before_prompt": cls.MIN_SUCCESS_BEFORE_PROMPT,
            "prompt_cooldown_sec": cls.PROMPT_COOLDOWN_SEC,
            "prompt_probability": cls.PROMPT_PROBABILITY,
            "contact_url": cls.CONTACT_URL,
        }


__all__ = ["FeedbackDefaults"]
