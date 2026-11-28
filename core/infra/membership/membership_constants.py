"""Membership token path and format (module-internal SSOT)."""

from __future__ import annotations

import re

TOKEN_FILE_NAME = "membership_token.txt"
RELATIVE_PATH = f"userspace/system/membership/{TOKEN_FILE_NAME}"
TOKEN_PATTERN = re.compile(r"^ntq_[0-9a-f]{48}$")

__all__ = ["RELATIVE_PATH", "TOKEN_FILE_NAME", "TOKEN_PATTERN"]