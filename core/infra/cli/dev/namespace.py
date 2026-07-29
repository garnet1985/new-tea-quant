"""Developer CLI public namespace (``Cli.dev``)."""

from __future__ import annotations

from core.infra.cli.dev.main import DevRunner


class DevNamespace:
    """Developer / ops CLI (``devcli.py``)."""

    @staticmethod
    def main(argv: list[str] | None = None) -> int:
        return DevRunner.main(argv)
