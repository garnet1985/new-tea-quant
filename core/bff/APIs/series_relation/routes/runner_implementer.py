"""Series relation run / results implementer."""

from __future__ import annotations

from typing import Any, Dict


class SeriesRelationRunnerImplementer:
    def __init__(self) -> None:
        self._Scenes = None

    def lazy_load(self) -> "SeriesRelationRunnerImplementer":
        if self._Scenes is None:
            from core.bff.APIs.series_relation.helpers.scenes import (
                SeriesRelationScenes,
            )

            self._Scenes = SeriesRelationScenes
        return self

    def run_scene(self, key: str) -> Dict[str, Any]:
        assert self._Scenes is not None
        return self._Scenes.run_scene(key)

    def get_results(self, key: str, *, max_points: int = 800) -> Dict[str, Any]:
        assert self._Scenes is not None
        return self._Scenes.get_results(key, max_points=max_points)


runner_impl = SeriesRelationRunnerImplementer()
