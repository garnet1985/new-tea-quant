"""run_series_relation：薄封装 SeriesRelation.run（同步跑批）。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.series_relation import SeriesRelation


def run_series_relation(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"key"}:
        return {"ok": False, "error": "只接受参数 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    out = SeriesRelation.run(key.strip())
    # Facade 用 success；信道统一成 ok，便于 agent 判断
    if isinstance(out, dict) and "ok" not in out and "success" in out:
        remapped = dict(out)
        remapped["ok"] = bool(out.get("success"))
        return remapped
    return out if isinstance(out, dict) else {"ok": False, "error": "跑批返回异常"}
