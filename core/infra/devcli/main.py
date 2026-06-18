"""Dev CLI entry."""

from __future__ import annotations

import sys

from core.infra.devcli.abbrev import expand_argv, is_help_argv
from core.infra.devcli.parser import build_parser, parse_args


def main(argv: list[str] | None = None) -> int:
    raw = list(argv if argv is not None else sys.argv[1:])
    if is_help_argv(raw):
        build_parser().print_help()
        return 0

    from devtools.quick_tools.publish_prep import parse_publish_argv, run_publish_prep

    pub, rest = parse_publish_argv(raw)
    if pub is not None:
        return run_publish_prep(pub)

    expanded = expand_argv(rest)
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
