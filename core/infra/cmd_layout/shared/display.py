"""终端显示宽度（CJK 全角计 2 列）。"""

from __future__ import annotations

import unicodedata


def display_width(text: str) -> int:
    """返回 ``text`` 在等宽终端中的列宽。"""
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            width += 2
        else:
            width += 1
    return width
