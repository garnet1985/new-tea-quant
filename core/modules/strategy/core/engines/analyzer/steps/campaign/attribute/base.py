"""战役归因基类：按层声明旋钮范围与结局，供收集和报告列使用。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ..metrics import READY


class AttributeBase:
    """一层战役归因。子类声明本层旋钮前缀与结局列。"""

    LAYER: str = ""
    KNOB_PREFIXES: Tuple[str, ...] = ()
    OUTCOMES: Tuple[Tuple[str, str], ...] = ()

    @classmethod
    def accepts_knob(cls, path: Any) -> bool:
        """该路径是否属于本层要看的旋钮。"""
        text = str(path or "").strip()
        if not text:
            return False
        if not cls.KNOB_PREFIXES:
            return True
        for prefix in cls.KNOB_PREFIXES:
            root = prefix[:-1] if prefix.endswith(".") else prefix
            if text == root or text.startswith(prefix):
                return True
        return False

    @classmethod
    def filter_knobs(cls, paths: Sequence[Any]) -> List[str]:
        """留下本层接受的旋钮路径。"""
        out: List[str] = []
        seen = set()
        for path in paths:
            text = str(path or "").strip()
            if not text or text in seen or not cls.accepts_knob(text):
                continue
            seen.add(text)
            out.append(text)
        return out

    @classmethod
    def run(cls, gathered: Mapping[str, Any]) -> Dict[str, Any]:
        """返回本层是否有足够格子可对照。"""
        rows = [
            row
            for row in gathered.get("rows") or []
            if isinstance(row, dict) and row.get("status") in READY
        ]
        n = len(rows)
        focus = cls.LAYER
        if n < 2:
            return {
                "status": "skipped",
                "reason": "insufficient_ready_rows",
                "n": n,
                "layer": focus,
                "layers": {},
            }
        usable = [
            row
            for row in rows
            if isinstance((row.get("layers") or {}).get(focus), dict)
        ]
        if focus and len(usable) < 2:
            skipped = {
                "status": "skipped",
                "reason": "insufficient_layer_rows",
                "n": len(usable),
            }
            return {
                "status": "skipped",
                "reason": "insufficient_layer_rows",
                "n": n,
                "layer": focus,
                "layers": {focus: skipped},
            }
        return {
            "status": "ok",
            "n": n,
            "layer": focus,
            "layers": {focus: {"status": "ok", "n": n}} if focus else {},
        }
