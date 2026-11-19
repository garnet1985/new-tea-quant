"""preview_data_rows：抽样读本机契约/行情行（验收用）。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.data_manager import DataManager


def preview_data_rows(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """按 data_key + 标的抽样若干行。当前优先支持 stock.kline.*。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"data_key", "entity_id", "limit", "start", "end", "term"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    data_key = args.get("data_key")
    if not isinstance(data_key, str) or not data_key.strip():
        return {"ok": False, "error": "data_key 不能为空"}
    data_key = data_key.strip()
    entity_id = args.get("entity_id")
    if not isinstance(entity_id, str) or not entity_id.strip():
        return {"ok": False, "error": "entity_id 不能为空（如 600036.SH）"}
    entity_id = entity_id.strip()

    limit = args.get("limit", 5)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        return {"ok": False, "error": "limit 须为正整数"}
    limit = min(limit, 20)

    start = args.get("start")
    end = args.get("end")
    for label, value in (("start", start), ("end", end)):
        if value is not None and not isinstance(value, str):
            return {"ok": False, "error": f"{label} 须为字符串日期 YYYYMMDD"}

    if data_key.startswith("stock.kline."):
        term = args.get("term")
        if term is None:
            term = data_key.rsplit(".", 1)[-1]
        if not isinstance(term, str) or not term.strip():
            return {"ok": False, "error": "term 无效"}
        term = term.strip()
        try:
            rows = DataManager().stock.kline.load(
                entity_id,
                term=term,
                start_date=str(start).strip() if start else None,
                end_date=str(end).strip() if end else None,
            )
        except Exception as exc:
            return {
                "ok": False,
                "data_key": data_key,
                "entity_id": entity_id,
                "error": f"无法读取 K 线: {exc}",
            }
        if not isinstance(rows, list):
            return {"ok": False, "error": "K 线返回格式异常"}
        sample = rows[-limit:] if rows else []
        return {
            "ok": True,
            "data_key": data_key,
            "entity_id": entity_id,
            "term": term,
            "total_loaded": len(rows),
            "returned": len(sample),
            "rows": [_row_brief(r) for r in sample],
            "note": "只读抽样，用于验收本机数据；不是实时行情。",
        }

    return {
        "ok": False,
        "data_key": data_key,
        "error": (
            f"暂不支持抽样 data_key={data_key}。"
            "当前支持 stock.kline.daily / weekly / monthly。"
        ),
    }


def _row_brief(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {"raw": str(row)[:200]}
    out: Dict[str, Any] = {}
    for key in (
        "trade_date",
        "date",
        "stock_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
    ):
        if key in row:
            out[key] = row.get(key)
    if not out:
        # 未知形状：截断表示
        for key, value in list(row.items())[:8]:
            if key in {"raw", "hfq", "adj_factor"}:
                continue
            out[str(key)] = value
    return out
