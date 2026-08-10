"""Best-effort setup Trace events (never affect install outcome)."""

from __future__ import annotations

from typing import Literal, Optional

InstallEntry = Literal["ui", "cli"]


class SetupTrace:
    """Setup / runtime Trace helpers（静态 API，勿实例化）。"""

    @staticmethod
    def install_complete(
        *,
        success: bool,
        entry: InstallEntry,
        error_code: Optional[str] = None,
    ) -> None:
        """Emit ``install.complete`` with stable, non-sensitive fields only."""
        try:
            from core.infra.trace import Trace

            body: dict = {
                "success": bool(success),
                "entry": entry,
            }
            if error_code:
                # Stable codes only (step id / stage name); never exception text.
                body["error_code"] = str(error_code)[:128]
            Trace.track("install.complete", body)
        except Exception:
            pass


__all__ = ["SetupTrace"]
