"""Expand short devcli tokens (``csc``) to long names."""

from __future__ import annotations

import re
from typing import Sequence

from core.infra.cli.dev.commands import DevCommands
from core.infra.cli.shared.abbrev import SharedNamespace

_PACK_VERSION_RE = re.compile(r"^-core_v(?P<ver>\d+\.\d+\.\d+)$")


class DevAbbrev:
    """Developer CLI argv expansion."""

    @staticmethod
    def _expand_pack_version_tokens(tokens: Sequence[str]) -> list[str]:
        out: list[str] = []
        for tok in tokens:
            m = _PACK_VERSION_RE.match(tok)
            if m:
                out.extend(["--version", m.group("ver")])
                continue
            out.append(tok)
        return out

    @staticmethod
    def _after_expand(out: list[str]) -> list[str]:
        if out and out[0] == "pack" and len(out) > 1:
            return [out[0], *DevAbbrev._expand_pack_version_tokens(out[1:])]
        return out

    @staticmethod
    def expand_argv(argv: Sequence[str]) -> list[str]:
        return SharedNamespace.expand_argv(
            argv,
            short_to_long=DevCommands.SHORT_TO_LONG,
            long_commands=DevCommands.LONG_COMMANDS,
            default_command=DevCommands.DEFAULT_COMMAND,
            version_argv=DevCommands.VERSION_ARGV,
            after_expand=DevAbbrev._after_expand,
        )

    @staticmethod
    def is_help_argv(argv: Sequence[str]) -> bool:
        return SharedNamespace.is_help_argv(argv)
