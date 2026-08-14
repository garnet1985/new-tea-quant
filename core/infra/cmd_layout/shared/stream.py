"""Shared stream helpers for CLI layout print paths."""

from __future__ import annotations

import sys
from typing import Optional, TextIO


class StreamWriter:
    """Print layout strings to a text stream (default stdout)."""

    @staticmethod
    def write(text: str, *, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        if text:
            print(text, file=out, flush=True)
        else:
            print(file=out, flush=True)
