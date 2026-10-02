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
    DEFAULT_H2_CHAR = "="
    DEFAULT_H2_MIN_WIDTH = 24
    DEFAULT_H3_CHAR = "-"
    DEFAULT_H4_PREFIX = "###"

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
    def h1(
        cls,
        text: str,
        *,
        char: str = DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
    ) -> str:
        """Report-level title: blank line, star box, blank line (via print)."""
        return "\n" + cls.banner(
            text, char=char, width=width, center=center, pad=pad
        )

    @classmethod
    def h2(
        cls,
        text: str,
        *,
        char: str = DEFAULT_H2_CHAR,
        min_width: int = DEFAULT_H2_MIN_WIDTH,
    ) -> str:
        """Major section: blank line, heading + underline."""
        body = str(text).strip()
        rule_char = (char or cls.DEFAULT_H2_CHAR)[:1] or "="
        rule_width = max(cls.display_width(body), max(1, int(min_width)))
        return f"\n{body}\n{rule_char * rule_width}"

    @classmethod
    def h3(
        cls,
        text: str,
        *,
        char: str = DEFAULT_H3_CHAR,
    ) -> str:
        """Minor section: blank line + ``--- heading ---``."""
        rule_char = (char or cls.DEFAULT_H3_CHAR)[:1] or "-"
        body = str(text).strip()
        deco = rule_char * 3
        return f"\n{deco} {body} {deco}"

    @classmethod
    def h4(
        cls,
        text: str,
        *,
        prefix: str = DEFAULT_H4_PREFIX,
    ) -> str:
        """Detail heading: blank line + ``### text``."""
        mark = str(prefix or cls.DEFAULT_H4_PREFIX).strip() or cls.DEFAULT_H4_PREFIX
        body = str(text).strip()
        return f"\n{mark} {body}"

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

    @classmethod
    def print_h1(
        cls,
        text: str,
        *,
        char: str = DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.h1(text, char=char, width=width, center=center, pad=pad)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_h2(
        cls,
        text: str,
        *,
        char: str = DEFAULT_H2_CHAR,
        min_width: int = DEFAULT_H2_MIN_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.h2(text, char=char, min_width=min_width)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_h3(
        cls,
        text: str,
        *,
        char: str = DEFAULT_H3_CHAR,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.h3(text, char=char)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_h4(
        cls,
        text: str,
        *,
        prefix: str = DEFAULT_H4_PREFIX,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.h4(text, prefix=prefix)
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
    def h1(
        text: str,
        *,
        char: str = Title.DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
    ) -> str:
        return Title.h1(text, char=char, width=width, center=center, pad=pad)

    @staticmethod
    def h2(
        text: str,
        *,
        char: str = Title.DEFAULT_H2_CHAR,
        min_width: int = Title.DEFAULT_H2_MIN_WIDTH,
    ) -> str:
        return Title.h2(text, char=char, min_width=min_width)

    @staticmethod
    def h3(
        text: str,
        *,
        char: str = Title.DEFAULT_H3_CHAR,
    ) -> str:
        return Title.h3(text, char=char)

    @staticmethod
    def h4(
        text: str,
        *,
        prefix: str = Title.DEFAULT_H4_PREFIX,
    ) -> str:
        return Title.h4(text, prefix=prefix)

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

    @staticmethod
    def print_h1(
        text: str,
        *,
        char: str = Title.DEFAULT_CHAR,
        width: Optional[int] = None,
        center: bool = False,
        pad: Optional[int] = None,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_h1(
            text, char=char, width=width, center=center, pad=pad, stream=stream
        )

    @staticmethod
    def print_h2(
        text: str,
        *,
        char: str = Title.DEFAULT_H2_CHAR,
        min_width: int = Title.DEFAULT_H2_MIN_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_h2(
            text, char=char, min_width=min_width, stream=stream
        )

    @staticmethod
    def print_h3(
        text: str,
        *,
        char: str = Title.DEFAULT_H3_CHAR,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_h3(text, char=char, stream=stream)

    @staticmethod
    def print_h4(
        text: str,
        *,
        prefix: str = Title.DEFAULT_H4_PREFIX,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Title.print_h4(text, prefix=prefix, stream=stream)
