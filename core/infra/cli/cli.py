"""Cli facade — user / dev / shared namespace API."""

from __future__ import annotations

from core.infra.cli.dev.namespace import DevNamespace
from core.infra.cli.shared.abbrev import SharedNamespace
from core.infra.cli.user.namespace import UserNamespace


class Cli:
    """NTQ CLI facade (user + developer entrypoints)."""

    user = UserNamespace
    dev = DevNamespace
    shared = SharedNamespace
