"""Dev CLI command registry."""

from __future__ import annotations

from core.infra.cli.shared.abbrev import SharedNamespace


class DevCommands:
    """Long names and short aliases for the developer CLI."""

    SHORT_TO_LONG: dict[str, str] = {
        "uk": "ui_kill",
        "ic": "check_import",
        "cgc": "clear_global_cache",
        "csc": "clear_strategy_cache",
        "cdc": "cache_clear_db",
        "cmc": "cache_clear_disk",
        "dbc": "db_checkpoint",
        "ex": "data_export_init",
        "pu": "userspace_package",
        "p": "pack",
        "ssp": "sample_stock_pool",
        "pc": "pool_clear",
        "cd": "check_deps",
    }

    LONG_COMMANDS: frozenset[str] = frozenset(
        {
            "version",
            "ui",
            "ui_kill",
            "check_import",
            "clear_global_cache",
            "clear_strategy_cache",
            "cache_clear_db",
            "cache_clear_disk",
            "db_checkpoint",
            "data_export_init",
            "userspace_package",
            "pack",
            "sample_stock_pool",
            "pool_clear",
            "check_deps",
        }
    )

    DEFAULT_COMMAND = "version"
    VERSION_ARGV = SharedNamespace.VERSION_ARGV

    @classmethod
    def aliases_for(cls, long_name: str) -> list[str]:
        return SharedNamespace.aliases_for(cls.SHORT_TO_LONG, long_name)
