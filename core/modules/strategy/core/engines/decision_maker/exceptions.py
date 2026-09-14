"""决策者用户可见错误。"""

from __future__ import annotations

from typing import Any, Dict, Sequence


class DecisionError(ValueError):
    """用户可见错误（中文）。"""


class AmbiguousSessionsError(DecisionError):
    """未指定 session 且有多局未完成。"""

    def __init__(self, sessions: Sequence[Dict[str, Any]]) -> None:
        self.sessions = list(sessions)
        ids = ", ".join(str(row.get("dm_id") or "") for row in self.sessions)
        super().__init__(f"有多局未完成（{ids}），请用 --session 指定")


__all__ = ["AmbiguousSessionsError", "DecisionError"]
