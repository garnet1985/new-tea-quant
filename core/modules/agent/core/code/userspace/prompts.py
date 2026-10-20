"""Userspace prompt 片段：只追加，冲突时以产品 prompt 为准。"""

from __future__ import annotations

import logging

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.modules.agent.core.code.conf.conf import (
    USERSPACE_PROMPT_LANES,
    USERSPACE_PROMPT_SNIPPET_MAX_CHARS,
)

logger = logging.getLogger(__name__)

_CONFLICT_HEADER = (
    "## 用户扩展（偏好；与上方冲突时以上方红线、协议与产品说明为准）"
)


def load_userspace_prompt_snippet(lane: str) -> str:
    key = str(lane or "").strip()
    if key not in USERSPACE_PROMPT_LANES:
        return ""
    if not ProjectContext.path.is_safe_extension_id(key):
        return ""
    path = ProjectContext.path.get_agent_prompts_directory() / f"{key}.md"
    if not path.is_file():
        return ""
    text = Discovery.file.load_text(path)
    if text is None:
        logger.warning("userspace prompt unreadable %s", path)
        return ""
    text = str(text).strip()
    if not text:
        return ""
    limit = int(USERSPACE_PROMPT_SNIPPET_MAX_CHARS)
    if len(text) > limit:
        logger.warning(
            "userspace prompt %s truncated from %s to %s chars",
            key,
            len(text),
            limit,
        )
        text = text[:limit].rstrip() + "\n…"
    return text


def append_userspace_prompt(base: str, lane: str) -> str:
    """把 userspace snippet 接到产品 prompt 末尾。"""
    body = str(base or "").rstrip()
    snippet = load_userspace_prompt_snippet(lane)
    if not snippet:
        return body
    block = f"{_CONFLICT_HEADER}\n\n{snippet}".rstrip()
    if not body:
        return block
    return f"{body}\n\n{block}"
