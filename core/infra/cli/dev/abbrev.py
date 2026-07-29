"""Expand short devcli tokens (``csc``) to long names."""

from __future__ import annotations

import re
from typing import Sequence

from core.infra.cli.dev.commands import (
    DEFAULT_COMMAND,
    LONG_COMMANDS,
    SHORT_TO_LONG,
    VERSION_ARGV,
)
from core.infra.cli.shared import expand_argv as _expand_argv
from core.infra.cli.shared import is_help_argv

_PACK_VERSION_RE = re.compile(r"^-core_v(?P<ver>\d+\.\d+\.\d+)$")


def _expand_pack_version_tokens(tokens: Sequence[str]) -> list[str]:
    out: list[str] = []
    for tok in tokens:
        m = _PACK_VERSION_RE.match(tok)
        if m:
            out.extend(["--version", m.group("ver")])
            continue
        out.append(tok)
    return out


def _after_expand(out: list[str]) -> list[str]:
    if out and out[0] == "pack" and len(out) > 1:
        return [out[0], *_expand_pack_version_tokens(out[1:])]
    return out


def expand_argv(argv: Sequence[str]) -> list[str]:
    """
    Normalize argv: first token may be a short command alias.

    Empty argv, ``-v``, ``--version`` → ``version``.
    ``p -core_v0.3.2`` → ``pack --version 0.3.2``.
    """
    return _expand_argv(
        argv,
        short_to_long=SHORT_TO_LONG,
        long_commands=LONG_COMMANDS,
        default_command=DEFAULT_COMMAND,
        version_argv=VERSION_ARGV,
        after_expand=_after_expand,
    )


__all__ = ["expand_argv", "is_help_argv"]
