"""User CLI public namespace (``Cli.user``)."""

from __future__ import annotations


class UserNamespace:
    """End-user CLI (``cli.py``)."""

    @staticmethod
    def ensure_venv(entry_file: str) -> None:
        """Re-exec into project venv when needed (light; safe before heavy imports)."""
        from core.infra.cli.user.bootstrap import UserBootstrap

        UserBootstrap.ensure_venv_for_cli(entry_file)

    @staticmethod
    def bootstrap(entry_file: str) -> None:
        from core.infra.cli.user.bootstrap import UserBootstrap

        UserBootstrap.ensure_venv_for_cli(entry_file)
        UserBootstrap.ensure_app_installed_if_needed()

    @staticmethod
    def main(argv: list[str] | None = None) -> int:
        from core.infra.cli.user.main import UserRunner

        return UserRunner.main(argv)
