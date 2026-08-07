"""Dev CLI entry."""

from __future__ import annotations

import sys

from core.infra.cli.dev.abbrev import DevAbbrev
from core.infra.cli.dev.parser import DevParser


class DevRunner:
    """Developer CLI main dispatch."""

    @staticmethod
    def main(argv: list[str] | None = None) -> int:
        raw = list(argv if argv is not None else sys.argv[1:])
        if DevAbbrev.is_help_argv(raw):
            DevParser.build_parser().print_help()
            return 0

        try:
            args = DevParser.parse_args(raw)
        except SystemExit as exc:
            code = exc.code
            return int(code) if isinstance(code, int) else 1

        handler = getattr(args, "handler", None)
        if handler is None:
            DevParser.build_parser().print_help()
            return 0

        return int(handler(args))
