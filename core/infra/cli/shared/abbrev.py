"""Shared CLI argv helpers (user + dev)."""

from __future__ import annotations

from typing import Callable, Mapping, Optional, Sequence


class SharedNamespace:
    """Shared argv scaffolding for user and dev CLIs."""

    VERSION_ARGV = frozenset({"-v", "--version"})

    @staticmethod
    def aliases_for(short_to_long: Mapping[str, str], long_name: str) -> list[str]:
        return sorted(
            short for short, long in short_to_long.items() if long == long_name
        )

    @staticmethod
    def expand_argv(
        argv: Sequence[str],
        *,
        short_to_long: Mapping[str, str],
        long_commands: frozenset[str],
        default_command: str = "version",
        version_argv: frozenset[str] | None = None,
        after_expand: Optional[Callable[[list[str]], list[str]]] = None,
    ) -> list[str]:
        """Normalize argv: first token may be a short command alias."""
        ver = (
            SharedNamespace.VERSION_ARGV
            if version_argv is None
            else version_argv
        )
        if not argv or (len(argv) == 1 and argv[0] in ver):
            return [default_command]

        out = list(argv)
        head = out[0]
        if head in short_to_long:
            out[0] = short_to_long[head]
        elif head not in long_commands and head not in ("-h", "--help", "help"):
            pass  # argparse will report unknown command

        if after_expand is not None:
            out = after_expand(out)
        return out

    @staticmethod
    def is_help_argv(argv: Sequence[str]) -> bool:
        return bool(argv) and argv[0] in ("-h", "--help", "help")
