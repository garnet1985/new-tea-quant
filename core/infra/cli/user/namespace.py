"""User CLI public namespace (``Cli.user``)."""

from __future__ import annotations

from core.infra.cli.user.bootstrap import UserBootstrap
from core.infra.cli.user.main import UserRunner


class UserNamespace:
    """End-user CLI (``cli.py``)."""

    @staticmethod
    def bootstrap(entry_file: str) -> None:
        UserBootstrap.ensure_venv_for_cli(entry_file)
        UserBootstrap.ensure_app_installed_if_needed()

    @staticmethod
    def main(argv: list[str] | None = None) -> int:
        return UserRunner.main(argv)
