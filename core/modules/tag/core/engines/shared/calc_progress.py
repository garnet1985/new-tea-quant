"""Tag 计算进度水位（incremental：上次算到的业务日，非 max(as_of)）。

``sys_tag_value.calculated_at`` 是落库墙钟时间；``sys_tag_scenario.updated_at``
仅随元数据变更。变化日写入的 tag 的 max(as_of) 也不等于「扫过的最后交易日」。

本模块按 entity 持久化 ``last_calculated_end``（YYYYMMDD），供 incremental 续跑。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, Mapping

from core.infra.project_context.core.path_manager import PathManager

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class TagCalcProgressStore:
    """``userspace/.ntq/tag_calc_progress/<scenario>.json``。"""

    @classmethod
    def _root(cls) -> Path:
        return PathManager.get_userspace_ntq_directory() / "tag_calc_progress"

    @classmethod
    def _path(cls, scenario_name: str) -> Path:
        raw = str(scenario_name or "").strip().replace("/", "__")
        safe = _SAFE_NAME.sub("_", raw).strip("._") or "unknown"
        return cls._root() / f"{safe}.json"

    @classmethod
    def load_entity_ends(cls, scenario_name: str) -> Dict[str, str]:
        path = cls._path(scenario_name)
        if not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("读取 tag calc progress 失败: %s (%s)", path, exc)
            return {}
        entities = raw.get("entities") if isinstance(raw, dict) else None
        if not isinstance(entities, dict):
            return {}
        out: Dict[str, str] = {}
        for eid, end in entities.items():
            key = str(eid or "").strip()
            val = str(end or "").strip()
            if key and val:
                out[key] = val
        return out

    @classmethod
    def clear(cls, scenario_name: str) -> None:
        path = cls._path(scenario_name)
        try:
            if path.is_file():
                path.unlink()
                logger.info("cleared tag calc progress: %s", scenario_name)
        except Exception as exc:
            logger.warning("清除 tag calc progress 失败: %s (%s)", path, exc)

    @classmethod
    def mark_entities(
        cls,
        scenario_name: str,
        entity_ends: Mapping[str, str],
    ) -> None:
        """将给定 entity 的「已算到」推进为至少 ``end``（取 max）。"""
        if not entity_ends:
            return
        current = cls.load_entity_ends(scenario_name)
        changed = False
        for eid, end in entity_ends.items():
            key = str(eid or "").strip()
            val = str(end or "").strip()
            if not key or not val:
                continue
            prev = current.get(key) or ""
            if (not prev) or val > prev:
                current[key] = val
                changed = True
        if not changed:
            return
        cls._write(scenario_name, current)

    @classmethod
    def _write(cls, scenario_name: str, entities: Dict[str, str]) -> None:
        path = cls._path(scenario_name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(
                    {"scenario": scenario_name, "entities": entities},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            tmp.replace(path)
        except Exception as exc:
            logger.warning("写入 tag calc progress 失败: %s (%s)", path, exc)


__all__ = ["TagCalcProgressStore"]
