"""
股票列表 Handler 辅助函数：数据格式化、维度表与映射表操作。
"""
from typing import List, Dict, Any, Optional, Tuple


# ========== 数据格式化 ==========


def format_mapped_records_with_defaults(
    mapped_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    补充 is_active，过滤无效记录。

    时间戳（last_update）由 Handler 在最终保存前统一打点，
    这里不提前写入，避免混淆「DB 里已有的 last_update」与「本批次写入时间」。
    """
    formatted = []
    for item in mapped_records:
        item["is_active"] = 1
        if item.get("id") and item.get("name"):
            formatted.append(item)
    return formatted


def build_main_records_and_dimensions(
    normalized_records: List[Dict[str, Any]],
    raw_records: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str, str]]]:
    """从 normalized + raw 构建 main_records（写 sys_stock_list）和 dimensions（stock_id, industry, board, market）。"""
    main_records = []
    dimensions: List[Tuple[str, str, str, str]] = []
    for i, r in enumerate(normalized_records):
        main_records.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "is_active": r.get("is_active", 1),
            "last_update": r.get("last_update"),
        })
        raw = raw_records[i] if i < len(raw_records) else {}
        dimensions.append((
            str(r.get("id") or ""),
            str(raw.get("industry", "未知行业")).strip() or "未知行业",
            str(raw.get("board", "未知板块")).strip() or "未知板块",
            str(raw.get("market", "未知市场")).strip() or "未知市场",
        ))
    return main_records, dimensions


def group_dimensions(dimensions: List[Tuple[str, str, str, str]]) -> Dict[str, List[str]]:
    """从 dimensions 提取去重后的 industry/board/market 值列表。"""
    return {
        "industry": list({d[1] for d in dimensions}),
        "board": list({d[2] for d in dimensions}),
        "market": list({d[3] for d in dimensions}),
    }


# ========== 维度表与映射表 ==========


def sync_dimension_is_alive(model, current_values: List[str], value_col: str = "value") -> None:
    """按当前批次同步 is_active：在 current_values 中的置 1，不在的置 0。"""
    if not hasattr(model, "update"):
        return
    if current_values:
        vals = tuple(current_values)
        model.update({"is_active": 0}, f'"{value_col}" NOT IN %s', (vals,))
        model.update({"is_active": 1}, f'"{value_col}" IN %s', (vals,))
    else:
        model.update({"is_active": 0}, "1=1", ())


def ensure_and_sync_dimension_batch(
    model, current_values: List[str], value_col: str = "value"
) -> Dict[str, int]:
    """
    批量确保维度表中有当前批次的值，同步 is_active，返回 {value: id}。
    IO: 1 次 load(已有) + 0~1 次 batch_insert(新值) + 0~1 次 load(新值 id) + 2 次 update(is_active)
    """
    if not current_values:
        sync_dimension_is_alive(model, [], value_col)
        return {}

    vals = tuple(current_values)
    existing = model.load(f'"{value_col}" IN %s', (vals,))
    val_to_id = {row[value_col]: int(row["id"]) for row in existing if row.get(value_col) and row.get("id")}
    in_db = set(val_to_id.keys())
    new_values = [v for v in current_values if v not in in_db]

    if new_values:
        rows = [{"value": v, "is_active": 1} for v in new_values]
        model.batch_insert(rows)
        new_rows = model.load(f'"{value_col}" IN %s', (tuple(new_values),))
        for row in new_rows:
            if row.get(value_col) and row.get("id"):
                val_to_id[row[value_col]] = int(row["id"])

    sync_dimension_is_alive(model, current_values, value_col)
    return {v: val_to_id[v] for v in current_values if v in val_to_id}


def ensure_and_sync_market_batch(model, current_values: List[str]) -> Dict[str, int]:
    """
    批量确保 sys_markets 中有当前批次的值，同步 is_active，返回 {value: id}。
    markets 表多 code 字段，新插入时 SSE/SZSE/BSE 填充 code。
    """
    if not current_values:
        sync_dimension_is_alive(model, [], "value")
        return {}

    vals = tuple(current_values)
    existing = model.load('"value" IN %s', (vals,))
    val_to_id = {row["value"]: int(row["id"]) for row in existing if row.get("value") and row.get("id")}
    in_db = set(val_to_id.keys())
    new_values = [v for v in current_values if v not in in_db]

    if new_values:
        rows = []
        for v in new_values:
            payload = {"value": v, "is_active": 1}
            if v in ("SSE", "SZSE", "BSE"):
                payload["code"] = v
            rows.append(payload)
        model.batch_insert(rows)
        new_rows = model.load('"value" IN %s', (tuple(new_values),))
        for row in new_rows:
            if row.get("value") and row.get("id"):
                val_to_id[row["value"]] = int(row["id"])

    sync_dimension_is_alive(model, current_values, "value")
    return {v: val_to_id[v] for v in current_values if v in val_to_id}




def save_stock_dimension_mappings(
    dimensions: List[Tuple[str, str, str, str]],
    val_to_id: Dict[str, Dict[str, int]],
    industry_map_model,
    board_map_model,
    market_map_model,
) -> None:
    """删除当前批次股票的旧映射，插入新映射。"""
    industry_val_to_id = val_to_id.get("industry") or {}
    board_val_to_id = val_to_id.get("board") or {}
    market_val_to_id = val_to_id.get("market") or {}

    industry_rows = []
    board_rows = []
    market_rows = []
    stock_ids = set()

    for stock_id, industry_val, board_val, market_val in dimensions:
        if not stock_id:
            continue
        stock_ids.add(stock_id)
        if industry_val_to_id.get(industry_val) is not None:
            industry_rows.append({"stock_id": stock_id, "industry_id": industry_val_to_id[industry_val]})
        if board_val_to_id.get(board_val) is not None:
            board_rows.append({"stock_id": stock_id, "board_id": board_val_to_id[board_val]})
        if market_val_to_id.get(market_val) is not None:
            market_rows.append({"stock_id": stock_id, "market_id": market_val_to_id[market_val]})

    if stock_ids:
        ids_tuple = tuple(stock_ids)
        industry_map_model.delete("stock_id IN %s", (ids_tuple,))
        board_map_model.delete("stock_id IN %s", (ids_tuple,))
        market_map_model.delete("stock_id IN %s", (ids_tuple,))

    if industry_rows:
        industry_map_model.replace_mapping(industry_rows)
    if board_rows:
        board_map_model.replace_mapping(board_rows)
    if market_rows:
        market_map_model.replace_mapping(market_rows)
