"""Shared CLI argv helpers (user + dev)."""

from __future__ import annotations

from typing import Callable, Mapping, Optional, Sequence

VERSION_ARGV = frozenset({"-v", "--version"})


def aliases_for(short_to_long: Mapping[str, str], long_name: str) -> list[str]:
    return sorted(short for short, long in short_to_long.items() if long == long_name)


def expand_argv(
    argv: Sequence[str],
    *,
    short_to_long: Mapping[str, str],
    long_commands: frozenset[str],
    default_command: str = "version",
    version_argv: frozenset[str] = VERSION_ARGV,
    after_expand: Optional[Callable[[list[str]], list[str]]] = None,
) -> list[str]:
    """Normalize argv: first token may be a short command alias."""
    if not argv or (len(argv) == 1 and argv[0] in version_argv):
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


def is_help_argv(argv: Sequence[str]) -> bool:
    return bool(argv) and argv[0] in ("-h", "--help", "help")


__all__ = [
    "VERSION_ARGV",
    "aliases_for",
    "expand_argv",
    "is_help_argv",
]
