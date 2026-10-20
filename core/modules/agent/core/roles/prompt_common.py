"""Shared helpers for building prompts (no long Chinese copy here)."""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.prompt_store import load_prompt


def product_identity_text() -> str:
    """Product identity + compliance block from ``prompts/common/identity.md``."""
    return load_prompt("common/identity.md").rstrip()


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
