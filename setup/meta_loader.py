from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict, deque

REPO_ROOT = Path(__file__).resolve().parent.parent
STEPS_ROOT = REPO_ROOT / "setup" / "steps"


def _topological_sort_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {step["id"]: step for step in steps}
    in_degree = {step["id"]: 0 for step in steps}
    graph: Dict[str, List[str]] = defaultdict(list)

    for step in steps:
        for dep in step.get("dependencies", []):
            if dep not in by_id:
                continue
            graph[dep].append(step["id"])
            in_degree[step["id"]] += 1

    def sort_key(step_id: str) -> tuple[int, str]:
        step = by_id[step_id]
        return (int(step.get("order", 9999)), step.get("name", step_id))

    queue = deque(sorted([sid for sid, deg in in_degree.items() if deg == 0], key=sort_key))
    result_ids: List[str] = []

    while queue:
        current = queue.popleft()
        result_ids.append(current)
        for nxt in sorted(graph[current], key=sort_key):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
        queue = deque(sorted(list(queue), key=sort_key))

    if len(result_ids) != len(steps):
        # 依赖图存在环时，回退到 order 排序，避免接口不可用
        return sorted(steps, key=lambda x: (int(x.get("order", 9999)), x.get("name", x.get("id", ""))))
    return [by_id[sid] for sid in result_ids]


def load_setup_step_meta(ui_only: bool = True) -> List[Dict[str, Any]]:
    metas: List[Dict[str, Any]] = []
    if not STEPS_ROOT.is_dir():
        return metas

    for child in STEPS_ROOT.iterdir():
        if not child.is_dir():
            continue
        meta_file = child / "meta.json"
        if not meta_file.is_file():
            continue
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            if ui_only and not bool(data.get("uiVisible", False)):
                continue
            metas.append(data)
        except Exception:
            continue

    metas = _topological_sort_steps(metas)
    for item in metas:
        item.pop("order", None)
        item.pop("uiVisible", None)
    return metas
