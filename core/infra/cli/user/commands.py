"""User CLI command registry."""

from __future__ import annotations

from core.infra.cli.shared.abbrev import SharedNamespace


class UserCommands:
    """Long names and short aliases for the user CLI."""

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
        "id": "import_data",
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
            "import_data",
            "update",
            "version",
        }
    )

    # CLI ``app.start``：仅这些「跑策略 / 跑 Tag」命令会上报（避免 version/renew 等噪声）。
    TRACE_RUN_COMMANDS: frozenset[str] = frozenset(
        {
            "scan",
            "strategy_enumerate",
            "strategy_price_factor",
            "strategy_portfolio",
            "strategy_simulate",
            "tag",
        }
    )

    EARLY_COMMANDS: frozenset[str] = frozenset(
        {
            "update",
            "version",
            "export_strategy",
            "import_strategy",
            "import_data",
        }
    )

    DEFAULT_COMMAND = "version"
    VERSION_ARGV = SharedNamespace.VERSION_ARGV

    @classmethod
    def aliases_for(cls, long_name: str) -> list[str]:
        return SharedNamespace.aliases_for(cls.SHORT_TO_LONG, long_name)
