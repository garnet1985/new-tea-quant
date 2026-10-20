"""Shared helpers for building prompts (no long Chinese copy here)."""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.executor.shared.prompt_loader import (
    load_prompt,
    load_section,
)


def product_identity_text() -> str:
    """红线 + 职责边界（注入 guider/worker system；不含越界固定回复全文）。"""
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
