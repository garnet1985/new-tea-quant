"""
股票列表 Handler

使用 Tushare Provider 获取股票列表（包含所有交易所）。
行业/板块/市场由定义表（sys_industries、sys_boards、sys_markets）与映射表维护，保存时一并写入。
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.data_class.api_job import ApiJob


class TushareStockListHandler(BaseHandler):
    """
    股票列表 Handler
    
    从 Tushare 获取股票列表（包含所有交易所的股票）。
    行业/板块/市场写入定义表与映射表，sys_stock_list 仅存 id、name、is_active、last_update。
    
    配置：renew type=refresh，ignore_fields=["industry","board","market"]，field_mapping 含 industry/board/market 文本。
    """
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        context["last_update"] = current_datetime
        return apis
    
    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        last_update = context.get("last_update") or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted = []
        for item in mapped_records:
            item["last_update"] = last_update
            item["is_active"] = 1
            if not item.get("industry"):
                item["industry"] = "未知行业"
            if not item.get("board"):
                item["board"] = "未知板块"
            if not item.get("market"):
                item["market"] = "未知市场"
            if item.get("id") and item.get("name"):
                formatted.append(item)
        logger.info(f"✅ 股票列表处理完成，共 {len(formatted)} 只股票（last_update: {last_update}）")
        return formatted
    
    def on_before_save(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """只返回写入 sys_stock_list 的 payload（id、name、is_active、last_update）；维度信息存 context 供 _do_save 写映射表。"""
        records = (normalized_data or {}).get("data") or []
        main_records = []
        dimensions: List[Tuple[str, str, str, str]] = []
        for r in records:
            main_records.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "is_active": r.get("is_active", 1),
                "last_update": r.get("last_update"),
            })
            dimensions.append((
                str(r.get("id") or ""),
                str(r.get("industry") or "未知行业").strip() or "未知行业",
                str(r.get("board") or "未知板块").strip() or "未知板块",
                str(r.get("market") or "未知市场").strip() or "未知市场",
            ))
        context["_stock_list_dimensions"] = dimensions
        return {"data": main_records}
    
    # TODO: 私有方法不应 override，后续改为扩展点（如 hook）后再在此写维度与映射表
    def _do_save(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """先写 sys_stock_list，再写行业/板块/市场定义与映射表。"""
        if self._is_dry_run():
            return normalized_data
        resolved = self.on_before_save(self.context, normalized_data)
        data_to_save = resolved if resolved is not None else normalized_data
        self._system_save(data_to_save)
        dimensions: List[Tuple[str, str, str, str]] = self.context.get("_stock_list_dimensions") or []
        if not dimensions:
            return data_to_save
        dm = self.context.get("data_manager")
        if not dm:
            return data_to_save
        industries_model = dm.get_table("sys_industries")
        boards_model = dm.get_table("sys_boards")
        markets_model = dm.get_table("sys_markets")
        industry_map_model = dm.get_table("sys_stock_industry_map")
        board_map_model = dm.get_table("sys_stock_board_map")
        market_map_model = dm.get_table("sys_stock_market_map")
        if not all([industries_model, boards_model, markets_model, industry_map_model, board_map_model, market_map_model]):
            logger.warning("缺少维度或映射表 Model，跳过维度与映射写入")
            return data_to_save
        industry_rows = []
        board_rows = []
        market_rows = []
        for stock_id, industry_val, board_val, market_val in dimensions:
            if not stock_id:
                continue
        stock_ids = list({s for s, _, _, _ in dimensions if s})
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
        return data_to_save
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        return normalized_data
