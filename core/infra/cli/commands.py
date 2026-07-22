"""CLI command registry: long names (underscore) and short aliases (no dash)."""

from __future__ import annotations

# xx = command, -xx = global/object flag, --xx = target param
SHORT_TO_LONG: dict[str, str] = {
    "c": "scan",
    "se": "strategy_enumerate",
    "sp": "strategy_price_factor",
    "so": "strategy_portfolio",
    "s": "strategy_simulate",
    "sy": "strategy_analyse",
    "r": "renew",
    "t": "tag",
    "ex": "export_strategy",
    "im": "import_strategy",
    "u": "update",
    "v": "version",
}

LONG_COMMANDS: frozenset[str] = frozenset(
    {
        "scan",
        "strategy_enumerate",
        "strategy_price_factor",
        "strategy_portfolio",
        "strategy_simulate",
        "strategy_analyse",
        "renew",
        "export_adj_factor",
        "tag",
        "export_strategy",
        "import_strategy",
        "update",
        "version",
    }
)

EARLY_COMMANDS: frozenset[str] = frozenset(
    {
        "update",
        "version",
        "export_strategy",
        "import_strategy",
    }
)

DEFAULT_COMMAND = "version"

VERSION_ARGV = frozenset({"-v", "--version"})


def aliases_for(long_name: str) -> list[str]:
    return sorted(short for short, long in SHORT_TO_LONG.items() if long == long_name)
