"""ASCII bar chart for CLI distribution / histogram output.

Cross-platform: fill/empty use plain ASCII so Windows GBK consoles stay safe.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence, TextIO, Tuple, Union

from core.infra.cmd_layout.shared.stream import StreamWriter

BucketInput = Union[
    "BarBucket",
    Tuple[str, float],
    Tuple[str, int],
    Mapping[str, object],
]


@dataclass(frozen=True)
class BarBucket:
    """One labeled bar (count or weight). Negative values are clamped to 0."""

    label: str
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", str(self.label))
        object.__setattr__(self, "value", max(0.0, float(self.value)))


class BarChart:
    """Render horizontal ASCII distribution bars for CLI reports."""

    FILL = "#"
    EMPTY = " "
    DEFAULT_WIDTH = 20

    @classmethod
    def render(
        cls,
        buckets: Sequence[BucketInput],
        *,
        title: str = "",
        width: int = DEFAULT_WIDTH,
        show_count: bool = True,
        show_pct: bool = True,
        skip_empty: bool = False,
        headers: Optional[Tuple[str, str, str, str]] = None,
    ) -> str:
        """Render pre-binned buckets to a multi-line ASCII chart string.

        ``headers``: optional ``(label, bar, count, pct)`` column titles.
        Pass ``""`` for unused columns (e.g. no bar title).
        """
        parsed = [cls._coerce_bucket(item) for item in buckets]
        if skip_empty:
            parsed = [b for b in parsed if b.value > 0]
        bar_width = max(1, int(width))

        lines: List[str] = []
        if title:
            lines.append(str(title))

        if not parsed:
            return "\n".join(lines)

        max_value = max(b.value for b in parsed)
        total = sum(b.value for b in parsed)
        label_width = max(len(b.label) for b in parsed)
        count_width = max(len(cls._format_count(b.value)) for b in parsed)
        if headers:
            h_label, h_bar, h_count, h_pct = headers
            label_width = max(label_width, len(str(h_label or "")))
            count_width = max(count_width, len(str(h_count or "")))
            bar_header = str(h_bar or "")
            bar_pad = max(bar_width + 2, len(bar_header))  # +2 for []
            header_row = f"  {str(h_label or ''):<{label_width}}  {bar_header:<{bar_pad}}"
            if show_count:
                header_row += f"  {str(h_count or ''):>{count_width}}"
            if show_pct:
                pct_h = str(h_pct or "")
                header_row += f"  {pct_h:>6}"
            lines.append(header_row)

        for bucket in parsed:
            filled = (
                bar_width
                if max_value <= 0
                else int(round((bucket.value / max_value) * bar_width))
            )
            filled = max(0, min(bar_width, filled))
            bar = f"[{cls.FILL * filled}{cls.EMPTY * (bar_width - filled)}]"
            if headers and headers[1]:
                bar_pad = max(bar_width + 2, len(str(headers[1])))
                bar = f"{bar:<{bar_pad}}"
            row = f"  {bucket.label:<{label_width}}  {bar}"
            if show_count:
                row += f"  {cls._format_count(bucket.value):>{count_width}}"
            if show_pct:
                pct = (bucket.value / total * 100.0) if total > 0 else 0.0
                row += f"  {pct:5.1f}%"
            lines.append(row)

        return "\n".join(lines)

    @classmethod
    def from_values(
        cls,
        values: Sequence[float],
        *,
        bins: int = 10,
        title: str = "",
        width: int = DEFAULT_WIDTH,
        show_count: bool = True,
        show_pct: bool = True,
        label_format: str = ".2f",
        skip_empty: bool = False,
    ) -> str:
        """Equal-width histogram from raw samples, then render."""
        buckets = cls._bin_values(values, bins=bins, label_format=label_format)
        return cls.render(
            buckets,
            title=title,
            width=width,
            show_count=show_count,
            show_pct=show_pct,
            skip_empty=skip_empty,
        )

    @classmethod
    def print(
        cls,
        buckets: Sequence[BucketInput],
        *,
        title: str = "",
        width: int = DEFAULT_WIDTH,
        show_count: bool = True,
        show_pct: bool = True,
        skip_empty: bool = False,
        headers: Optional[Tuple[str, str, str, str]] = None,
        stream: Optional[TextIO] = None,
    ) -> str:
        """Render pre-binned buckets and print to stream (default stdout)."""
        text = cls.render(
            buckets,
            title=title,
            width=width,
            show_count=show_count,
            show_pct=show_pct,
            skip_empty=skip_empty,
            headers=headers,
        )
        cls._write(text, stream=stream)
        return text

    @classmethod
    def print_from_values(
        cls,
        values: Sequence[float],
        *,
        bins: int = 10,
        title: str = "",
        width: int = DEFAULT_WIDTH,
        show_count: bool = True,
        show_pct: bool = True,
        label_format: str = ".2f",
        skip_empty: bool = False,
        stream: Optional[TextIO] = None,
    ) -> str:
        """Histogram from raw samples, print to stream (default stdout)."""
        text = cls.from_values(
            values,
            bins=bins,
            title=title,
            width=width,
            show_count=show_count,
            show_pct=show_pct,
            label_format=label_format,
            skip_empty=skip_empty,
        )
        cls._write(text, stream=stream)
        return text

    @classmethod
    def _bin_values(
        cls,
        values: Sequence[float],
        *,
        bins: int,
        label_format: str,
    ) -> List[BarBucket]:
        samples = [float(v) for v in values]
        if not samples:
            return []

        n_bins = max(1, int(bins))
        lo = min(samples)
        hi = max(samples)

        if math.isclose(lo, hi):
            label = cls._format_edge(lo, label_format)
            return [BarBucket(f"[{label}]", float(len(samples)))]

        width = (hi - lo) / n_bins
        counts = [0] * n_bins
        for value in samples:
            if value >= hi:
                idx = n_bins - 1
            else:
                idx = int((value - lo) / width)
                idx = max(0, min(n_bins - 1, idx))
            counts[idx] += 1

        buckets: List[BarBucket] = []
        for i, count in enumerate(counts):
            left = lo + i * width
            right = hi if i == n_bins - 1 else lo + (i + 1) * width
            left_s = cls._format_edge(left, label_format)
            right_s = cls._format_edge(right, label_format)
            # Last bin closed on both sides; others half-open [left, right).
            closer = "]" if i == n_bins - 1 else ")"
            label = f"[{left_s}, {right_s}{closer}"
            buckets.append(BarBucket(label, float(count)))
        return buckets

    @staticmethod
    def _format_edge(value: float, label_format: str) -> str:
        # Accept ".2f" or ":.2f" (f-string style); format() wants no leading colon.
        fmt = label_format[1:] if label_format.startswith(":") else label_format
        return format(value, fmt)

    @staticmethod
    def _format_count(value: float) -> str:
        if float(value).is_integer():
            return str(int(value))
        return f"{value:.2f}"

    @classmethod
    def _coerce_bucket(cls, item: BucketInput) -> BarBucket:
        if isinstance(item, BarBucket):
            return item
        if isinstance(item, Mapping):
            label = item.get("label", item.get("name", ""))
            value = item.get("value", item.get("count", 0))
            return BarBucket(str(label), float(value or 0))
        if isinstance(item, tuple) and len(item) == 2:
            return BarBucket(str(item[0]), float(item[1]))
        raise TypeError(
            f"Unsupported bucket input: {type(item)!r}; "
            "expected BarBucket, (label, value), or mapping"
        )

    @staticmethod
    def _write(text: str, *, stream: Optional[TextIO] = None) -> None:
        StreamWriter.write(text, stream=stream)


class BarChartNamespace:
    """CmdLayout.bar_chart namespace — thin wrappers over BarChart."""

    @staticmethod
    def render(
        buckets: Sequence[BucketInput],
        *,
        title: str = "",
        width: int = BarChart.DEFAULT_WIDTH,
        show_count: bool = True,
        show_pct: bool = True,
        skip_empty: bool = False,
        headers: Optional[Tuple[str, str, str, str]] = None,
    ) -> str:
        return BarChart.render(
            buckets,
            title=title,
            width=width,
            show_count=show_count,
            show_pct=show_pct,
            skip_empty=skip_empty,
            headers=headers,
        )

    @staticmethod
    def from_values(
        values: Sequence[float],
        *,
        bins: int = 10,
        title: str = "",
        width: int = BarChart.DEFAULT_WIDTH,
        show_count: bool = True,
        show_pct: bool = True,
        label_format: str = ".2f",
        skip_empty: bool = False,
    ) -> str:
        return BarChart.from_values(
            values,
            bins=bins,
            title=title,
            width=width,
            show_count=show_count,
            show_pct=show_pct,
            label_format=label_format,
            skip_empty=skip_empty,
        )

    @staticmethod
    def print(
        buckets: Sequence[BucketInput],
        *,
        title: str = "",
        width: int = BarChart.DEFAULT_WIDTH,
        show_count: bool = True,
        show_pct: bool = True,
        skip_empty: bool = False,
        headers: Optional[Tuple[str, str, str, str]] = None,
        stream: Optional[TextIO] = None,
    ) -> str:
        return BarChart.print(
            buckets,
            title=title,
            width=width,
            show_count=show_count,
            show_pct=show_pct,
            skip_empty=skip_empty,
            headers=headers,
            stream=stream,
        )

    @staticmethod
    def print_from_values(
        values: Sequence[float],
        *,
        bins: int = 10,
        title: str = "",
        width: int = BarChart.DEFAULT_WIDTH,
        show_count: bool = True,
        show_pct: bool = True,
        label_format: str = ".2f",
        skip_empty: bool = False,
        stream: Optional[TextIO] = None,
    ) -> str:
        return BarChart.print_from_values(
            values,
            bins=bins,
            title=title,
            width=width,
            show_count=show_count,
            show_pct=show_pct,
            label_format=label_format,
            skip_empty=skip_empty,
            stream=stream,
        )


__all__ = ["BarBucket", "BarChart", "BarChartNamespace", "BucketInput"]
