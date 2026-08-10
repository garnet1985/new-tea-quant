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

        show_help_before_version = not raw
        try:
            args = DevParser.parse_args(raw)
        except SystemExit as exc:
            code = exc.code
            return int(code) if isinstance(code, int) else 1

        handler = getattr(args, "handler", None)
        if handler is None:
            DevParser.build_parser().print_help()
            return 0

        if show_help_before_version and args.command == "version":
            DevParser.build_parser().print_help()
            print()

        try:
            from setup.trace_events import SetupTrace

            SetupTrace.app_start(entry="devcli")
        except Exception:
            pass

        return int(handler(args))
