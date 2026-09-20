"""决策者 CLI 数字格式。

本文件:
- format_date / format_money / format_pct / format_shares
  边界: 只做字符串；不读盘、不改会话
"""

from __future__ import annotations

from typing import Optional


def format_date(value: str) -> str:
    raw = str(value or "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw or "—"


def format_money(value: float) -> str:
    return f"{float(value):,.2f}"


def format_pct(ratio: Optional[float], *, signed: bool = False) -> str:
    if ratio is None:
        return "—"
    pct = float(ratio) * 100.0
    if signed:
        return f"{pct:+.1f}%"
    return f"{pct:.0f}%"


def format_shares(shares: int) -> str:
    return f"{int(shares):,}"


__all__ = ["format_date", "format_money", "format_pct", "format_shares"]
