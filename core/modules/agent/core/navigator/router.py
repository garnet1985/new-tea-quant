"""Navigator：意图 → 有序处理清单。补全打当前 Provider（由调用方传入）。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core.modules.agent.core.navigator import patterns as P
from core.modules.agent.core.navigator.classifier import classify_route, sort_pipeline
from core.modules.agent.core.roles.guide.patterns import is_architecture_question

# regex = 强制正则兜底（对照/离线）；默认走模型分流
_NAV_MODE_ENV = "NTQ_AGENT_NAVIGATOR_MODE"


@dataclass(frozen=True)
class Route:
    """有序清单：``kind`` 为当前先执行项；``queue`` 为完整排队。"""

    kind: str
    queue: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.queue:
            object.__setattr__(self, "queue", (self.kind,))


def route(
    text: str,
    *,
    provider_id: str,
    mode: Optional[str] = None,
) -> Route:
    """``provider_id`` 必须是本次锁定的唯一 Provider。"""
    raw = str(text or "").strip()
    if not raw:
        return Route("guide")

    key = (mode or _mode_from_env()).strip().lower()
    if key == "regex":
        return regex_route(raw)

    pid = str(provider_id or "").strip()
    if not pid:
        return regex_route(raw)

    kinds = classify_route(raw, provider_id=pid)
    if kinds:
        return _route_from_kinds(_escalate_queue(raw, kinds))
    return regex_route(raw)


def regex_route(text: str) -> Route:
    """正则辅助：仅对照/失败兜底。"""
    raw = str(text or "").strip()
    if not raw:
        return Route("guide")
    return _route_from_kinds(_detect_regex_kinds(raw))


def _route_from_kinds(kinds: List[str]) -> Route:
    ordered = sort_pipeline(kinds) or ["guide"]
    return Route(kind=ordered[0], queue=tuple(ordered))


def _detect_regex_kinds(raw: str) -> List[str]:
    found: List[str] = []
    if P.is_investment_advice_trap(raw):
        found.append("advice")
    if P.is_out_of_scope_web_question(raw):
        found.append("out_of_scope")
    if is_architecture_question(raw):
        found.append("guide_arch")
    if P.is_product_identity_question(raw):
        found.append("identity")
    if P.force_worker(raw):
        found.append("worker")
    if not found:
        found.append("guide")
    return found


def _escalate_queue(text: str, kinds: List[str]) -> List[str]:
    merged = list(kinds)
    if P.is_investment_advice_trap(text) and "advice" not in merged:
        merged.insert(0, "advice")
    if P.is_out_of_scope_web_question(text) and "out_of_scope" not in merged:
        merged.append("out_of_scope")
    return sort_pipeline(merged)


def _mode_from_env() -> str:
    raw = os.environ.get(_NAV_MODE_ENV, "").strip().lower()
    if raw == "regex":
        return "regex"
    return "model"
