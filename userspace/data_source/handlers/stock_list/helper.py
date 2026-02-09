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
