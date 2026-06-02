"""主进程 spill / Worker 侧加载（可选优化路径，待 profiling 后再启用）。"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Mapping

from core.infra.job_dispatcher.types import DataRef

_JSON_ROWS = "json_rows"
_SAFE_PART = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_part(value: str) -> str:
    return _SAFE_PART.sub("_", value).strip("_") or "slot"


def spill_slot_rows(
    spill_root: Path,
    job_id: str,
    slot_data: Mapping[str, List[dict]],
) -> List[DataRef]:
    """将 slot → rows 写入 spill_root/<job_id>/*.json，返回 DataRef 列表。"""
    job_dir = Path(spill_root) / _safe_part(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    refs: List[DataRef] = []
    for slot, rows in slot_data.items():
        path = job_dir / f"{_safe_part(slot)}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(list(rows or []), handle, ensure_ascii=False)
        refs.append(
            DataRef(
                slot=str(slot),
                uri=str(path.resolve()),
                meta={"format": _JSON_ROWS},
            )
        )
    return refs


def load_slot_rows(data_refs: List[DataRef]) -> Dict[str, List[dict]]:
    """按 DataRef 读回 slot → rows。"""
    out: Dict[str, List[dict]] = {}
    for ref in data_refs:
        fmt = (ref.meta or {}).get("format", _JSON_ROWS)
        if fmt != _JSON_ROWS:
            raise ValueError(f"Unsupported spill format: {fmt!r}")
        with Path(ref.uri).open(encoding="utf-8") as handle:
            out[ref.slot] = json.load(handle)
    return out


def load_slot_rows_from_payload(inject_block: dict) -> Dict[str, List[dict]]:
    """从 payload['_inject']['data_refs'] 读回 rows（Worker 侧）。"""
    raw_refs = inject_block.get("data_refs") or []
    refs = [
        DataRef(
            slot=str(item["slot"]),
            uri=str(item["uri"]),
            meta=dict(item.get("meta") or {}),
        )
        for item in raw_refs
    ]
    return load_slot_rows(refs)


def cleanup_data_refs(data_refs: List[DataRef]) -> None:
    """删除单个 job 的 spill 目录。"""
    if not data_refs:
        return
    job_dir = Path(data_refs[0].uri).parent
    if job_dir.is_dir():
        shutil.rmtree(job_dir, ignore_errors=True)


def cleanup_spill_root(spill_root: Path) -> None:
    """删除整次 run 的 spill 根目录。"""
    root = Path(spill_root)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)
