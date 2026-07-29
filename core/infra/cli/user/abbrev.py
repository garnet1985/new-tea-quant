"""Expand short user-CLI tokens (``sp``) to long names."""

from __future__ import annotations

from typing import Sequence

from core.infra.cli.shared import expand_argv as _expand_argv
from core.infra.cli.shared import is_help_argv
from core.infra.cli.user.commands import (
    DEFAULT_COMMAND,
    LONG_COMMANDS,
    SHORT_TO_LONG,
    VERSION_ARGV,
)


def expand_argv(argv: Sequence[str]) -> list[str]:
    """
    Normalize argv: first token may be a short command alias.

    ``sp -f --strategy demo`` → ``strategy_price_factor -f --strategy demo``
    Empty argv, ``-v``, ``--version`` → ``version``.
    """
    return _expand_argv(
        argv,
        short_to_long=SHORT_TO_LONG,
        long_commands=LONG_COMMANDS,
        default_command=DEFAULT_COMMAND,
        version_argv=VERSION_ARGV,
    )


__all__ = ["expand_argv", "is_help_argv"]
