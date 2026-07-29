"""Expand short user-CLI tokens (``sp``) to long names."""

from __future__ import annotations

from typing import Sequence

from core.infra.cli.shared.abbrev import SharedNamespace
from core.infra.cli.user.commands import UserCommands


class UserAbbrev:
    """User CLI argv expansion."""

    @staticmethod
    def expand_argv(argv: Sequence[str]) -> list[str]:
        return SharedNamespace.expand_argv(
            argv,
            short_to_long=UserCommands.SHORT_TO_LONG,
            long_commands=UserCommands.LONG_COMMANDS,
            default_command=UserCommands.DEFAULT_COMMAND,
            version_argv=UserCommands.VERSION_ARGV,
        )

    @staticmethod
    def is_help_argv(argv: Sequence[str]) -> bool:
        return SharedNamespace.is_help_argv(argv)
