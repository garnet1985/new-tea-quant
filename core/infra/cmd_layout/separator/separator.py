"""ASCII separator / divider layouts for CLI report presentation."""
from __future__ import annotations

from typing import Optional, TextIO

from core.infra.cmd_layout.shared.stream import StreamWriter


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
        rule_char = (char or cls.LINE_CHAR)[:1] or "-"
        return rule_char * max(1, int(width))

    @classmethod
    def thick(
        cls,
        *,
        width: int = DEFAULT_WIDTH,
    ) -> str:
        return cls.line(char=cls.THICK_CHAR, width=width)

    @classmethod
    def star(
        cls,
        *,
        width: int = DEFAULT_WIDTH,
    ) -> str:
        return cls.line(char=cls.STAR_CHAR, width=width)

    @classmethod
    def blank(cls) -> str:
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
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_thick(
        cls,
        *,
        width: int = DEFAULT_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.thick(width=width)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_star(
        cls,
        *,
        width: int = DEFAULT_WIDTH,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.star(width=width)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_blank(cls, *, stream: Optional[TextIO] = None) -> str:
        out = cls.blank()
        StreamWriter.write(out, stream=stream)
        return out


class SeparatorNamespace:
    """CmdLayout.separator namespace."""

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
