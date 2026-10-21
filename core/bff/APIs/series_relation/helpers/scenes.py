"""SeriesRelation 场景列表 / 读写 / 跑批 — 只经 Facade。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.modules.series_relation import SeriesRelation


class SeriesRelationScenes:
    @classmethod
    def list_items(cls) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for info in SeriesRelation.list_infos():
            results = SeriesRelation.load_results(info.key)
            items.append(
                {
                    "key": info.key,
                    "display_name": info.display_name,
                    "relative_path": info.relative_path,
                    "has_results": bool(results.get("has_results")),
                }
            )
        return items

    @classmethod
    def fetch_page(
        cls, page: int, limit: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        ordered = cls.list_items()
        total = len(ordered)
        start = max(0, (int(page) - 1) * int(limit))
        end = start + max(1, int(limit))
        return ordered[start:end], total

    @classmethod
    def get_scene(cls, key: str) -> Dict[str, Any]:
        info = SeriesRelation.find(key)
        if info is None:
            return {"success": False, "error": f"未找到: {key}"}
        results = SeriesRelation.load_results(info.key)
        return {
            "success": True,
            "key": info.key,
            "display_name": info.display_name,
            "relative_path": info.relative_path,
            "settings": info.settings,
            "has_results": bool(results.get("has_results")),
            "max_series": SeriesRelation.MAX_SERIES,
        }

    @classmethod
    def save_scene(cls, key: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        return SeriesRelation.save(key, settings)

    @classmethod
    def run_scene(cls, key: str) -> Dict[str, Any]:
        return SeriesRelation.run(key)

    @classmethod
    def get_results(cls, key: str, *, max_points: int = 800) -> Dict[str, Any]:
        return SeriesRelation.load_results(key, max_points=max_points)
