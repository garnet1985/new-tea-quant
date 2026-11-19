"""BFF tag async shell：薄封装，编排在 ``Tag`` Facade。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.tag import Tag


class TagRunLauncher:
    """UI 异步跑 tag：委托 ``Tag.trigger_run`` / ``start_run`` / ``get_run_progress``。"""

    @classmethod
    def trigger(cls, *, tag_key: str) -> Dict[str, Any]:
        return Tag.trigger_run(tag_key=tag_key)

    @classmethod
    def start_now(cls, *, tag_key: str) -> Dict[str, Any]:
        return Tag.start_run(tag_key=tag_key)

    @classmethod
    def get_progress(cls, *, tag_key: str, job_id: str) -> Optional[Dict[str, Any]]:
        return Tag.get_run_progress(tag_key=tag_key, job_id=job_id)


__all__ = ["TagRunLauncher"]
