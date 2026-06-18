"""Expand short command tokens (``sp``) to long names (``strategy_price_factor``)."""

from __future__ import annotations

from typing import Sequence

from core.infra.cli.commands import DEFAULT_COMMAND, LONG_COMMANDS, SHORT_TO_LONG, VERSION_ARGV


def expand_argv(argv: Sequence[str]) -> list[str]:
    """
    Normalize argv: first token may be a short command alias.

    ``sp -f --strategy demo`` → ``strategy_price_factor -f --strategy demo``
    Empty argv, ``-v``, ``--version`` → ``version``.
    """
    if not argv or (len(argv) == 1 and argv[0] in VERSION_ARGV):
        return [DEFAULT_COMMAND]

    out = list(argv)
    head = out[0]
    if head in SHORT_TO_LONG:
        out[0] = SHORT_TO_LONG[head]
    elif head not in LONG_COMMANDS and head not in ("-h", "--help", "help"):
        pass  # argparse will report unknown command
    return out


def is_help_argv(argv: Sequence[str]) -> bool:
    return bool(argv) and argv[0] in ("-h", "--help", "help")
