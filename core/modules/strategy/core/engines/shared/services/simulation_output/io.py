"""version 产物边界 IO（无 schema）。

消费者: enumerator, price_factor, portfolio
边界: 只做 json / 文本行读写；不解释业务字段
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence


class ArtifactIO:
    """json / 文本行边界读写（布局服务 namespace）。"""

    @classmethod
    def read_json(cls, path: Path) -> Dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def write_json(cls, path: Path, payload: Any) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target

    @classmethod
    def read_text_lines(cls, path: Path) -> List[str]:
        target = Path(path)
        if not target.is_file():
            return []
        return [
            line.strip()
            for line in target.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @classmethod
    def write_text_lines(cls, path: Path, lines: Sequence[str]) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        cleaned = [str(x).strip() for x in lines if str(x).strip()]
        target.write_text(
            "\n".join(cleaned) + ("\n" if cleaned else ""),
            encoding="utf-8",
        )
        return target


__all__ = ["ArtifactIO"]
