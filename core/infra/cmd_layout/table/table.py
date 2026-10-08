"""ASCII table layouts for CLI report presentation."""
from __future__ import annotations

from typing import List, Optional, Sequence, TextIO

from core.infra.cmd_layout.shared.stream import StreamWriter
from core.infra.cmd_layout.title.title import Title


class Table:
    """Render simple ASCII tables (first column left, others right)."""

    DEFAULT_INDENT = 3
    DEFAULT_GAP = 2

    @classmethod
    def render(
        cls,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        indent: int = DEFAULT_INDENT,
        gap: int = DEFAULT_GAP,
    ) -> str:
        if not headers:
            return ""
        header_cells = [str(h) for h in headers]
        body_rows = [[str(cell) for cell in row] for row in rows]
        widths = [Title.display_width(h) for h in header_cells]
        for row in body_rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], Title.display_width(cell))
                else:
                    widths.append(Title.display_width(cell))
        pad = " " * max(0, int(indent))
        sep = " " * max(1, int(gap))

        def fmt(row: Sequence[str]) -> str:
            parts: List[str] = []
            for i, cell in enumerate(row):
                width = widths[i] if i < len(widths) else Title.display_width(cell)
                text = str(cell)
                pad_cols = max(0, width - Title.display_width(text))
                if i == 0:
                    parts.append(text + (" " * pad_cols))
                else:
                    parts.append((" " * pad_cols) + text)
            return pad + sep.join(parts)

        lines = [fmt(header_cells)]
        lines.append(pad + sep.join("-" * w for w in widths))
        for row in body_rows:
            # Align short rows to header column count.
            padded = list(row) + [""] * max(0, len(header_cells) - len(row))
            lines.append(fmt(padded[: len(header_cells)]))
        return "\n".join(lines)

    @classmethod
    def print(
        cls,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        indent: int = DEFAULT_INDENT,
        gap: int = DEFAULT_GAP,
        stream: Optional[TextIO] = None,
    ) -> str:
        out = cls.render(headers, rows, indent=indent, gap=gap)
        if out:
            StreamWriter.write(out, stream=stream)
        return out


class TableNamespace:
    """CmdLayout.table namespace."""

    @staticmethod
    def render(
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        indent: int = Table.DEFAULT_INDENT,
        gap: int = Table.DEFAULT_GAP,
    ) -> str:
        return Table.render(headers, rows, indent=indent, gap=gap)

    @staticmethod
    def print(
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        indent: int = Table.DEFAULT_INDENT,
        gap: int = Table.DEFAULT_GAP,
        stream: Optional[TextIO] = None,
    ) -> str:
        return Table.print(
            headers, rows, indent=indent, gap=gap, stream=stream
        )


__all__ = ["Table", "TableNamespace"]
