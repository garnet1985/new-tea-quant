"""Developer CLI public namespace (``Cli.dev``)."""

from __future__ import annotations


class DevNamespace:
    """Developer / ops CLI (``devcli.py``)."""

    @staticmethod
    def main(argv: list[str] | None = None) -> int:
        from core.modules.cli.dev.main import DevRunner

        return DevRunner.main(argv)
