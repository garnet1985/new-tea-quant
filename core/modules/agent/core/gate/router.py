"""外层路由：固定处理或交给 guide / worker。"""

from __future__ import annotations

from dataclasses import dataclass

from core.modules.agent.core.gate import patterns as P
from core.modules.agent.core.roles.guide.patterns import is_architecture_question


@dataclass(frozen=True)
class Route:
    """``kind``: identity | advice | out_of_scope | guide_arch | worker | guide."""

    kind: str


def route(text: str) -> Route:
    raw = str(text or "").strip()
    # 架构优先于身份（「NTQ 架构是什么」含品牌+是什么，但应走 guide_arch）。
    if is_architecture_question(raw):
        return Route("guide_arch")
    if P.is_product_identity_question(raw):
        return Route("identity")
    if P.is_investment_advice_trap(raw):
        return Route("advice")
    if P.is_out_of_scope_web_question(raw):
        return Route("out_of_scope")
    # 架构已处理；此处避免「含回测字样」把讲原理误送 worker。
    if P.force_worker(raw):
        return Route("worker")
    return Route("guide")
