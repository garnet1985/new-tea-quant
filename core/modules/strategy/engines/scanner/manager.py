#!/usr/bin/env python3
"""Scanner engine manager bridge."""

from .scanner import Scanner


class ScannerManager(Scanner):
    """Bridge manager backed by legacy scanner implementation."""

