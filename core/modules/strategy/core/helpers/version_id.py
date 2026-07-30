"""Workbench snapshot version_id parsing (``v3`` / ``3`` → int)."""

from __future__ import annotations

from typing import Optional


class WorkbenchVersionId:
    """Parse workbench snapshot version tokens used in BFF paths / launcher."""

    @staticmethod
    def parse(version_id: str) -> Optional[int]:
        """Accept ``v3`` / ``3`` forms; return positive int or ``None``."""
        text = str(version_id or "").strip()
        if not text:
            return None
        if text.lower().startswith("v"):
            text = text[1:]
        try:
            n = int(text)
            return n if n > 0 else None
        except ValueError:
            return None


__all__ = ["WorkbenchVersionId"]
