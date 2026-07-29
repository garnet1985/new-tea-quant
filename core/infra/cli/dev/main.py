"""Dev CLI entry."""

from __future__ import annotations

import sys

from core.infra.cli.dev.abbrev import DevAbbrev
from core.infra.cli.dev.parser import build_parser, parse_args


class DevRunner:
    """Developer CLI main dispatch."""

    @staticmethod
    def main(argv: list[str] | None = None) -> int:
        raw = list(argv if argv is not None else sys.argv[1:])
        if DevAbbrev.is_help_argv(raw):
            build_parser().print_help()
            return 0

        expanded = DevAbbrev.expand_argv(raw)
        try:
            args = parse_args(expanded)
        except SystemExit as exc:
            code = exc.code
            return int(code) if isinstance(code, int) else 1

        handler = getattr(args, "handler", None)
        if handler is None:
            build_parser().print_help()
            return 0

        return int(handler(args))
