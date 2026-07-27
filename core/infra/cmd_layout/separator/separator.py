"""ASCII separator / divider layouts for CLI report presentation."""
from __future__ import annotations

import sys
from typing import Optional, TextIO


class Separator:
    """Render ASCII divider lines for CLI reports."""

    DEFAULT_WIDTH = 60
    LINE_CHAR = "-"
    THICK_CHAR = "="
    STAR_CHAR = "*"

    @classmethod
    def line(
        cls,
        *,
        char: str = LINE_CHAR,
        width: int = DEFAULT_WIDTH,
    ) -> str:
        """Single horizontal rule, e.g. ``--------------------``."""
        rule_char = (char or cls.LINE_CHAR)[:1] or "-"
        return rule_char * max(1, int(width))

    @classmethod
    def thick(
        cls,
        *,
        width: int = DEFAULT_WIDTH,
    ) -> str:
        """Thick rule using ``=``."""
        return cls.line(char=cls.THICK_CHAR, width=width)

    @classmethod
    def star(
        cls,
        *,
        width: int = DEFAULT_WIDTH,
    ) -> str:
        """Star rule using ``*`` (matches title banner style)."""
        return cls.line(char=cls.STAR_CHAR, width=width)

    @classmethod
    def blank(cls) -> str:
        """Empty line (one newline when printed)."""
        return ""

    @classmethod
    def print_line(
        cls,
        *,
        char: str = LINE_CHAR,
        width: int = DEFAULT_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.line(char=char, width=width)
        cls._write(out, stream=stream)
        return out

    @classmethod
    def print_thick(
        cls,
        *,
        width: int = DEFAULT_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.thick(width=width)
        cls._write(out, stream=stream)
        return out

    @classmethod
    def print_star(
        cls,
        *,
        width: int = DEFAULT_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.star(width=width)
        cls._write(out, stream=stream)
        return out

    @classmethod
    def print_blank(cls, *, stream: Optional[TextIO] = None) -> str:
        out = cls.blank()
        cls._write(out, stream=stream)
        return out

    @staticmethod
    def _write(text: str, *, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        print(text, file=out, flush=True)


class SeparatorNamespace:
    """CmdLayout.separator namespace — thin wrappers over Separator."""

    @staticmethod
    def line(
        *,
        char: str = Separator.LINE_CHAR,
        width: int = Separator.DEFAULT_WIDTH,
    ) -> str:
        return Separator.line(char=char, width=width)

    @staticmethod
    def thick(*, width: int = Separator.DEFAULT_WIDTH) -> str:
        return Separator.thick(width=width)

    @staticmethod
    def star(*, width: int = Separator.DEFAULT_WIDTH) -> str:
        return Separator.star(width=width)

    @staticmethod
    def blank() -> str:
        return Separator.blank()

    @staticmethod
    def print_line(
        *,
        char: str = Separator.LINE_CHAR,
        width: int = Separator.DEFAULT_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Separator.print_line(char=char, width=width, stream=stream)

    @staticmethod
    def print_thick(
        *,
        width: int = Separator.DEFAULT_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Separator.print_thick(width=width, stream=stream)

    @staticmethod
    def print_star(
        *,
        width: int = Separator.DEFAULT_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Separator.print_star(width=width, stream=stream)

    @staticmethod
    def print_blank(*, stream: Optional[TextIO] = None) -> str:
        return Separator.print_blank(stream=stream)


__all__ = ["Separator", "SeparatorNamespace"]
