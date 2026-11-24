"""本轮对话绑定的远端 policy sections（由 ntq_external 门面提供）。

Agent 不实现官网协议；只在 run 期间把 sections 挂到 contextvar 供 prompt/reply 读取。
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Dict, Iterator, Mapping, Optional

_sections: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "ntq_agent_policy_sections", default=None
)


def active_policy_sections() -> Optional[Dict[str, Any]]:
    raw = _sections.get()
    return dict(raw) if isinstance(raw, dict) else None


def bind_policy_sections(sections: Optional[Mapping[str, Any]]) -> Token:
    if sections is None:
        return _sections.set(None)
    return _sections.set(dict(sections))


def reset_policy_sections(token: Token) -> None:
    _sections.reset(token)


@contextmanager
def policy_sections_scope(
    sections: Optional[Mapping[str, Any]],
) -> Iterator[None]:
    token = bind_policy_sections(sections)
    try:
        yield
    finally:
        reset_policy_sections(token)
