"""Cli facade — user / dev / shared namespace API."""

from __future__ import annotations

from core.modules.cli.dev.namespace import DevNamespace
from core.modules.cli.shared.abbrev import SharedNamespace
from core.modules.cli.user.namespace import UserNamespace


class Cli:
    """NTQ CLI facade (user + developer entrypoints)."""

    user = UserNamespace
    dev = DevNamespace
    shared = SharedNamespace
