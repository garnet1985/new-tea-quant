"""Shared CLI scaffolding used by user and dev entrypoints."""

from .abbrev import VERSION_ARGV, aliases_for, expand_argv, is_help_argv

__all__ = [
    "VERSION_ARGV",
    "aliases_for",
    "expand_argv",
    "is_help_argv",
]
