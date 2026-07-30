"""Query-string parsers for strategy routes."""

from __future__ import annotations

from typing import Optional


def parse_bool_query(v: Optional[str], default: bool = False) -> bool:
    if v is None:
        return default
    raw = str(v).strip().lower()
    if raw == "":
        return default
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False
    return default
