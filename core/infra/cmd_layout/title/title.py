"""ASCII title layouts for CLI report presentation."""
from __future__ import annotations

import unicodedata
from typing import Optional, TextIO

from core.infra.cmd_layout.shared.stream import StreamWriter


class Title:
    """Render ASCII title blocks for CLI reports."""

    DEFAULT_CHAR = "*"
    DEFAULT_SECTION_CHAR = "-"
    DEFAULT_BANNER_PAD = 16

    @staticmethod
    def display_width(text: str) -> int:
        """Terminal column width (CJK fullwidth counts as 2)."""
        width = 0
        for ch in text:
            if unicodedata.east_asian_width(ch) in ("F", "W"):
                width += 2
            else:
                width += 1
        return width

    @classmethod
    def banner(
        cls,
        text: str,
        *,
        char: str = DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
    ) -> str:
        body = str(text)
        rule_char = (char or cls.DEFAULT_CHAR)[:1] or "*"
        body_width = Title.display_width(body)
        if width is not None:
            rule_width = max(1, int(width))
        else:
            side_pad = cls.DEFAULT_BANNER_PAD if pad is None else max(0, int(pad))
            rule_width = max(1, body_width + side_pad)
        rule = rule_char * rule_width
        if center and body_width < rule_width:
            gap = rule_width - body_width
            left = gap // 2
            right = gap - left
            body = f"{' ' * left}{body}{' ' * right}"
        return f"{rule}\n{body}\n{rule}"

    @classmethod
    def section(
        cls,
        text: str,
        *,
        char: str = DEFAULT_SECTION_CHAR,
    ) -> str:
        rule_char = (char or cls.DEFAULT_SECTION_CHAR)[:1] or "-"
        body = str(text).strip()
        return f"{rule_char * 2} {body} {rule_char * 2}"

    @classmethod
    def print_banner(
        cls,
        text: str,
        *,
        char: str = DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.banner(text, char=char, width=width, center=center, pad=pad)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_section(
        cls,
        text: str,
        *,
        char: str = DEFAULT_SECTION_CHAR,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.section(text, char=char)
        StreamWriter.write(out, stream=stream)
        return out


class TitleNamespace:
    """CmdLayout.title namespace."""

    @staticmethod
    def banner(
        text: str,
        *,
        char: str = Title.DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
    ) -> str:
        return Title.banner(text, char=char, width=width, center=center, pad=pad)

    @staticmethod
    def section(
        text: str,
        *,
        char: str = Title.DEFAULT_SECTION_CHAR,
    ) -> str:
        return Title.section(text, char=char)

    @staticmethod
    def print_banner(
        text: str,
        *,
        char: str = Title.DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_banner(
            text, char=char, width=width, center=center, pad=pad, stream=stream
        )

    @staticmethod
    def print_section(
        text: str,
        *,
        char: str = Title.DEFAULT_SECTION_CHAR,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_section(text, char=char, stream=stream)
