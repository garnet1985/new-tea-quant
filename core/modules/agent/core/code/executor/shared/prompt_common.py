"""Shared helpers for building prompts (no long Chinese copy here)."""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.executor.shared.prompt_loader import (
    load_prompt,
    load_section,
)
from core.modules.agent.core.code.policy_bind import active_policy_sections


def product_identity_text() -> str:
    """红线 + 职责边界（注入 guider/worker system；不含越界固定回复全文）。

    产品态（会员）优先用 ntq_external 下发的 sections；框架态读本地 md。
    """
    remote = active_policy_sections()
    if remote:
        redlines = str(remote.get("redlines") or "").rstrip()
        can_do = str(remote.get("responsibility_can_do") or "").strip()
        cannot_do = str(remote.get("responsibility_cannot_do") or "").strip()
        if not can_do:
            can_do = load_section("global/responsibility.md", "can_do")
        if not cannot_do:
            cannot_do = load_section("global/responsibility.md", "cannot_do")
    else:
        redlines = load_prompt("global/redlines.md").rstrip()
        can_do = load_section("global/responsibility.md", "can_do")
        cannot_do = load_section("global/responsibility.md", "cannot_do")
    try:
        ext = load_section("global/responsibility.md", "userspace_extensions")
    except KeyError:
        ext = ""
    body = (
        f"{redlines}\n\n"
        f"## 职责·能做\n{can_do}\n\n"
        f"## 职责·不做\n{cannot_do}"
    )
    if ext.strip():
        body += f"\n\n## 用户扩展免责\n{ext.strip()}"
    disc = ""
    if remote and isinstance(remote.get("disclaimers"), dict):
        disc = str(remote["disclaimers"].get("specific") or "").strip()
    if disc:
        body += f"\n\n## 特定免责（产品准则）\n{disc}"
    return body.rstrip()


def param_text(schema: Dict[str, Any]) -> str:
    props = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(props, dict) or not props:
        return "无"
    required = set(schema.get("required") or [])
    bits = []
    for name, meta in props.items():
        desc = ""
        if isinstance(meta, dict):
            desc = str(meta.get("description") or "").strip()
        mark = "" if name in required else "，可省略"
        bits.append(f"{name}（{desc}{mark}）" if desc else f"{name}{mark}")
    return "；".join(bits)
