"""NTQ CLIs: user (``cli.py``) and dev (``devcli.py``).

Layout::

    shared/  — argv expand / help helpers
    user/    — end-user commands
    dev/     — developer / ops commands

Public API: ``from core.infra.cli import Cli``.
"""

from .cli import Cli

__all__ = ["Cli"]
