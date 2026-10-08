"""Inline text helpers for CLI report presentation."""
from __future__ import annotations

from typing import Any, Optional, Sequence, TextIO

from core.infra.cmd_layout.shared.stream import StreamWriter


class Text:
    """Render plain text fragments used across report presenters."""

    DEFAULT_INDENT = 3
    META_SEP = " · "
    BULLET = "-"

    @classmethod
    def meta(cls, parts: Sequence[Any], *, sep: str = META_SEP) -> str:
        bits = [str(part).strip() for part in parts if str(part or "").strip()]
        return sep.join(bits)

    @classmethod
    def kv(
        cls,
        label: Any,
        value: Any,
        *,
        sep: str = ": ",
    ) -> str:
        return f"{str(label).rstrip()}{sep}{value}"

    @classmethod
    def indent(
        cls,
        line: Any,
        *,
        spaces: int = DEFAULT_INDENT,
    ) -> str:
        pad = " " * max(0, int(spaces))
        text = str(line)
        if not text:
            return pad
        return "\n".join(pad + row if row else pad for row in text.splitlines())

    @classmethod
    def numbered(
        cls,
        items: Sequence[Any],
        *,
        indent: int = 0,
        empty: str = "",
    ) -> str:
        rows = [str(item) for item in items if str(item or "").strip()]
        if not rows:
            return cls.indent(empty, spaces=indent) if empty else ""
        pad = " " * max(0, int(indent))
        return "\n".join(f"{pad}{i}. {row}" for i, row in enumerate(rows, start=1))

    @classmethod
    def bullets(
        cls,
        items: Sequence[Any],
        *,
        indent: int = 0,
        marker: str = BULLET,
        empty: str = "",
    ) -> str:
        rows = [str(item) for item in items if str(item or "").strip()]
        if not rows:
            return cls.indent(empty, spaces=indent) if empty else ""
        pad = " " * max(0, int(indent))
        mark = str(marker or cls.BULLET)
        return "\n".join(f"{pad}{mark} {row}" for row in rows)

    @classmethod
    def print_meta(
        cls,
        parts: Sequence[Any],
        *,
        sep: str = META_SEP,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.meta(parts, sep=sep)
        if out:
            StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_kv(
        cls,
        label: Any,
        value: Any,
        *,
        sep: str = ": ",
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.kv(label, value, sep=sep)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_indent(
        cls,
        line: Any,
        *,
        spaces: int = DEFAULT_INDENT,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.indent(line, spaces=spaces)
        StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_numbered(
        cls,
        items: Sequence[Any],
        *,
        indent: int = 0,
        empty: str = "",
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.numbered(items, indent=indent, empty=empty)
        if out:
            StreamWriter.write(out, stream=stream)
        return out

    @classmethod
    def print_bullets(
        cls,
        items: Sequence[Any],
        *,
        indent: int = 0,
        marker: str = BULLET,
        empty: str = "",
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.bullets(items, indent=indent, marker=marker, empty=empty)
        if out:
            StreamWriter.write(out, stream=stream)
        return out


class TextNamespace:
    """CmdLayout.text namespace."""

    @staticmethod
    def meta(parts: Sequence[Any], *, sep: str = Text.META_SEP) -> str:
        return Text.meta(parts, sep=sep)

    @staticmethod
    def kv(label: Any, value: Any, *, sep: str = ": ") -> str:
        return Text.kv(label, value, sep=sep)

    @staticmethod
    def indent(line: Any, *, spaces: int = Text.DEFAULT_INDENT) -> str:
        return Text.indent(line, spaces=spaces)

    @staticmethod
    def numbered(
        items: Sequence[Any],
        *,
        indent: int = 0,
        empty: str = "",
    ) -> str:
        return Text.numbered(items, indent=indent, empty=empty)

    @staticmethod
    def bullets(
        items: Sequence[Any],
        *,
        indent: int = 0,
        marker: str = Text.BULLET,
        empty: str = "",
    ) -> str:
        return Text.bullets(
            items, indent=indent, marker=marker, empty=empty
        )

    @staticmethod
    def print_meta(
        parts: Sequence[Any],
        *,
        sep: str = Text.META_SEP,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Text.print_meta(parts, sep=sep, stream=stream)

    @staticmethod
    def print_kv(
        label: Any,
        value: Any,
        *,
        sep: str = ": ",
        stream: Optional[TextIO] = None,
    ) -> str:
        return Text.print_kv(label, value, sep=sep, stream=stream)

    @staticmethod
    def print_indent(
        line: Any,
        *,
        spaces: int = Text.DEFAULT_INDENT,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Text.print_indent(line, spaces=spaces, stream=stream)

    @staticmethod
    def print_numbered(
        items: Sequence[Any],
        *,
        indent: int = 0,
        empty: str = "",
        stream: Optional[TextIO] = None,
    ) -> str:
        return Text.print_numbered(
            items, indent=indent, empty=empty, stream=stream
        )

    @staticmethod
    def print_bullets(
        items: Sequence[Any],
        *,
        indent: int = 0,
        marker: str = Text.BULLET,
        empty: str = "",
        stream: Optional[TextIO] = None,
    ) -> str:
        return Text.print_bullets(
            items,
            indent=indent,
            marker=marker,
            empty=empty,
            stream=stream,
        )


__all__ = ["Text", "TextNamespace"]
