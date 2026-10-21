"""SeriesRelation Facade。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from core.infra.project_context import ProjectContext
from core.modules.series_relation.core.constants import MAX_SERIES
from core.modules.series_relation.core.discovery.discovered import DiscoveredRelation
from core.modules.series_relation.core.discovery.discovery_service import DiscoveryService
from core.modules.series_relation.core.persist.settings_io import write_settings_py
from core.modules.series_relation.core.pipeline.runner import run_relation
from core.modules.series_relation.core.settings.relation_settings import validate_settings

_SAFE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]*$")


class SeriesRelation:
    """多序列并置比较门面。"""

    MAX_SERIES = MAX_SERIES

    @staticmethod
    def list_infos() -> List[DiscoveredRelation]:
        return DiscoveryService.discover(
            declaration_lookup=SeriesRelation._declaration_lookup()
        )

    @staticmethod
    def list_keys() -> List[str]:
        return [item.key for item in SeriesRelation.list_infos()]

    @staticmethod
    def find(key_or_id: str) -> Optional[DiscoveredRelation]:
        return DiscoveryService.find(
            key_or_id,
            declaration_lookup=SeriesRelation._declaration_lookup(),
        )

    @staticmethod
    def validate(settings: Mapping[str, Any]) -> Dict[str, Any]:
        """返回 ``{ok, settings|None, errors}``。"""
        normalized, errors = validate_settings(
            settings,
            declaration_lookup=SeriesRelation._declaration_lookup(),
        )
        return {
            "ok": not errors and normalized is not None,
            "settings": normalized,
            "errors": errors,
        }

    @staticmethod
    def save(key_or_id: str, settings: Mapping[str, Any]) -> Dict[str, Any]:
        """校验并写入 ``userspace/extensions/series_relation/<key>/settings.py``。

        ``meta.key`` 强制与路径 key 一致；目录不存在则创建。
        """
        key = str(key_or_id or "").strip().strip("/")
        if not key or not _SAFE_KEY.match(key) or ".." in key:
            return {
                "success": False,
                "error": f"非法 key: {key_or_id!r}",
            }
        raw = dict(settings or {})
        meta = dict(raw.get("meta") or {}) if isinstance(raw.get("meta"), Mapping) else {}
        meta["key"] = key
        if not str(meta.get("display_name") or "").strip():
            meta["display_name"] = key
        raw["meta"] = meta

        checked = SeriesRelation.validate(raw)
        if not checked.get("ok") or not checked.get("settings"):
            return {
                "success": False,
                "key": key,
                "errors": list(checked.get("errors") or []),
                "error": "; ".join(checked.get("errors") or ["校验失败"]),
            }
        normalized = dict(checked["settings"])
        settings_path = ProjectContext.path.get_series_relation_settings_path(key)
        try:
            write_settings_py(settings_path, normalized)
        except Exception as exc:
            return {"success": False, "key": key, "error": str(exc)}
        return {
            "success": True,
            "key": key,
            "relative_path": key,
            "settings_path": str(settings_path),
            "settings": normalized,
        }

    @staticmethod
    def run(key_or_id: str) -> Dict[str, Any]:
        """发现场景并写入 ``results/``。"""
        info = SeriesRelation.find(key_or_id)
        if info is None:
            return {
                "success": False,
                "error": f"未找到 series_relation: {key_or_id}",
            }
        out = ProjectContext.path.get_series_relation_results_directory(
            info.relative_path
        )
        try:
            return run_relation(info.settings, output_dir=Path(out))
        except Exception as exc:
            return {"success": False, "key": info.key, "error": str(exc)}

    @staticmethod
    def load_results(
        key_or_id: str,
        *,
        max_points: int = 800,
    ) -> Dict[str, Any]:
        """读取最近一次跑批产物（供 UI 图 + report）。"""
        info = SeriesRelation.find(key_or_id)
        if info is None:
            return {
                "success": False,
                "error": f"未找到 series_relation: {key_or_id}",
            }
        results_dir = Path(
            ProjectContext.path.get_series_relation_results_directory(
                info.relative_path
            )
        )
        meta_path = results_dir / "meta.json"
        if not meta_path.is_file():
            return {
                "success": True,
                "key": info.key,
                "has_results": False,
                "results_dir": str(results_dir),
            }
        meta = _read_json(meta_path) or {}
        summary = _read_json(results_dir / "summary.json") or {}
        series_doc = _read_json(results_dir / "series.json") or {}
        report_path = results_dir / "report.txt"
        report = (
            report_path.read_text(encoding="utf-8")
            if report_path.is_file()
            else ""
        )
        chart = _chart_payload(series_doc, max_points=max(50, int(max_points)))
        return {
            "success": True,
            "key": info.key,
            "has_results": True,
            "results_dir": str(results_dir),
            "meta": meta,
            "summary": summary,
            "chart": chart,
            "report": report,
        }

    @staticmethod
    def _declaration_lookup():
        def lookup(data_key: str) -> Optional[Mapping[str, Any]]:
            try:
                from core.modules.data_contract import ContractIssuer
                from core.infra.project_context import ProjectContext as PC

                issuer = ContractIssuer()
                issuer.discover(user_space_path=PC.path.get_data_contract_root())
                if not issuer.is_available(data_key):
                    pass
                try:
                    return issuer.get_declaration(data_key)
                except Exception:
                    return None
            except Exception:
                return None

        return lookup


def _read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _chart_payload(series_doc: Mapping[str, Any], *, max_points: int) -> Dict[str, Any]:
    calendar = list(series_doc.get("calendar") or [])
    series_list = list(series_doc.get("series") or [])
    n = len(calendar)
    step = 1
    if n > max_points:
        step = max(1, n // max_points)
    picked_idx = list(range(0, n, step))
    if n and picked_idx[-1] != n - 1:
        picked_idx.append(n - 1)
    picked_dates = [calendar[i] for i in picked_idx if i < n]
    date_set = set(picked_dates)
    out_series = []
    for item in series_list:
        if not isinstance(item, Mapping):
            continue
        points = []
        for pt in item.get("points") or []:
            if not isinstance(pt, Mapping):
                continue
            day = str(pt.get("date") or "")
            if day not in date_set:
                continue
            points.append({"date": day, "norm": pt.get("norm"), "raw": pt.get("raw")})
        out_series.append(
            {
                "id": item.get("id"),
                "label": item.get("label"),
                "points": points,
            }
        )
    return {"calendar": picked_dates, "series": out_series, "point_step": step}


__all__ = ["SeriesRelation"]

