"""Expand short devcli tokens (``csc``) to long names (``clear_strategy_cache``)."""

from __future__ import annotations

import re
from typing import Sequence

from core.infra.devcli.commands import DEFAULT_COMMAND, LONG_COMMANDS, SHORT_TO_LONG, VERSION_ARGV

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


def expand_argv(argv: Sequence[str]) -> list[str]:
    """
    Normalize argv: first token may be a short command alias.

    Empty argv, ``-v``, ``--version`` → ``version``.
    ``p -core_v0.3.2`` → ``pack --version 0.3.2``.
    """
    if not argv or (len(argv) == 1 and argv[0] in VERSION_ARGV):
        return [DEFAULT_COMMAND]

    out = list(argv)
    head = out[0]
    if head in SHORT_TO_LONG:
        out[0] = SHORT_TO_LONG[head]
    elif head not in LONG_COMMANDS and head not in ("-h", "--help", "help"):
        pass

    if out[0] == "pack" and len(out) > 1:
        out[1:] = _expand_pack_version_tokens(out[1:])
    return out


def is_help_argv(argv: Sequence[str]) -> bool:
    return bool(argv) and argv[0] in ("-h", "--help", "help")
