"""Tag runner implementer (T1-02 / T1-03)."""

from __future__ import annotations

from typing import Any, Dict, Optional


class TagRunnerImplementer:
    def __init__(self) -> None:
        self._TagRunLauncher = None

    def lazy_load(self) -> "TagRunnerImplementer":
        if self._TagRunLauncher is None:
            from core.bff.APIs.tag.routes.runner.tag_run import TagRunLauncher

            self._TagRunLauncher = TagRunLauncher
        return self

    def trigger_run(self, *, tag_key: str) -> Dict[str, Any]:
        assert self._TagRunLauncher is not None
        return self._TagRunLauncher.trigger(tag_key=tag_key)

    def get_progress(
        self, *, tag_key: str, job_id: str
    ) -> Optional[Dict[str, Any]]:
        assert self._TagRunLauncher is not None
        return self._TagRunLauncher.get_progress(tag_key=tag_key, job_id=job_id)


impl = TagRunnerImplementer()
