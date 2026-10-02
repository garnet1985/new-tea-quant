"""User CLI command registry."""

from __future__ import annotations

from core.modules.cli.shared.abbrev import SharedNamespace


class UserCommands:
    """Long names and short aliases for the user CLI."""

    SHORT_TO_LONG: dict[str, str] = {
        "c": "scan",
        "se": "strategy_enumerate",
        "sp": "strategy_price_factor",
        "so": "strategy_portfolio",
        "s": "strategy_simulate",
        "sea": "strategy_attribute_enumerate",
        "spa": "strategy_attribute_price",
        "soa": "strategy_attribute_portfolio",
        "sw": "strategy_rolling",
        "sd": "strategy_decision",
        "sdl": "strategy_decision_list",
        "sdd": "strategy_decision_delete",
        "sdv": "strategy_delete_version",
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
            "strategy_decision",
            "strategy_decision_list",
            "strategy_decision_delete",
            "strategy_simulate",
            "strategy_attribute_enumerate",
            "strategy_attribute_price",
            "strategy_attribute_portfolio",
            "strategy_rolling",
            "strategy_delete_version",
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
            "strategy_attribute_enumerate",
            "strategy_attribute_price",
            "strategy_attribute_portfolio",
            "strategy_rolling",
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
