"""Expand devcli abbrev flags into semantic ``domain verb`` argv."""

from __future__ import annotations

from typing import Sequence

_SIMPLE: dict[str, list[str]] = {
    "-ui": ["ui", "run"],
    "-kui": ["ui", "kill"],
    "-ic": ["check", "import"],
    "-cc": ["cache", "clear-global"],
    "-csc": ["cache", "clear-simulation"],
    "-cdc": ["cache", "clear-db"],
    "-cmc": ["cache", "clear-disk"],
    "-dbc": ["db", "checkpoint"],
    "-userspace": ["userspace", "package"],
    "-ex": ["data", "export-init"],
    "-ssl": ["pool", "sample"],
    "-sample_stock_list": ["pool", "sample"],
}


def expand_argv(argv: Sequence[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in _SIMPLE:
            out.extend(_SIMPLE[tok])
            i += 1
            if tok in ("-ssl", "-sample_stock_list") and i < len(argv):
                nxt = argv[i]
                if nxt == "-clear":
                    out = ["pool", "clear"]
                    i += 1
                elif nxt.startswith("-") and nxt[1:].isdigit():
                    out.append(nxt[1:])
                    i += 1
            continue
        out.append(tok)
        i += 1
    return out


def is_help_argv(argv: Sequence[str]) -> bool:
    return bool(argv) and argv[0] in ("-h", "--help", "help")
