"""
股票列表 Handler

使用 Tushare Provider 获取股票列表（包含所有交易所）。
流程：on_before_run 检查 sys_cache -> 若今日已更新则从 DB 返回短路；否则 API -> on_before_save 写维度/映射/cache。
"""
from typing import List, Dict, Any, Optional, Set, Tuple
import logging

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.utils.date.date_utils import DateUtils

from .helper import (
    format_mapped_records_with_defaults,
    save_stock_dimension_mappings,
)

logger = logging.getLogger(__name__)

CACHE_KEY = "stock_list_last_update"
CACHE_DATE_FIELD = "last_checked_at"     # 缓存日期字段


class TushareStockListHandler(BaseHandler):
    """
    股票列表 Handler

    流程：on_before_run 检查 sys_cache，若今日已更新则从 DB 返回短路；否则 API -> on_before_save 写维度/映射/cache。
    """

    def on_before_run(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """若 sys_cache 记录今日已更新，则从 DB 读取并返回，跳过 API 调用。"""
        dm = context["data_manager"]
        try:
            cache = dm.db_cache.load(CACHE_KEY, field="json")
            if self._is_valid_cache(cache):
                data = dm.stock.list.load_all()
                logger.info(f"✅ stock_list 命中缓存，从 DB 直接返回（共 {len(data) if data else 0} 只）")
                return {"data": data}
            logger.info("ℹ️ stock_list 缓存校验失败，本次将调用 API 更新缓存")
        except Exception:
            pass
        return None

    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted = self._format_and_store_raw_records(context, mapped_records)
        logger.info(f"✅ 股票列表字段映射完成，共 {len(formatted)} 只股票")
        return formatted

    def on_before_save(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """1. 同步维度表（boards/markets/industries）；2. 写 stock_list；3. 写映射表；4. 写 cache。返回 main_records 供 base 的 _system_save 写入。"""
        dm = context["data_manager"]
        main_records = normalized_data.get("data", [])
        if not main_records:
            return {"data": []}

        # save 入口统一打本批次的 last_update 时间戳
        time_str = DateUtils.today()
        for r in main_records:
            r["last_update"] = time_str

        if context.get("is_dry_run"):
            return {"data": main_records}

        raw_records = context.get("_stock_list_raw_records") or []
        boards, markets, industries = self._group_boards_markets_and_industries(raw_records)

        list_svc = dm.stock.list
        board_val_to_id = list_svc.ensure_and_sync_boards(boards)
        market_val_to_id = list_svc.ensure_and_sync_markets(markets)
        industry_val_to_id = list_svc.ensure_and_sync_industries(industries)

        dimensions = self._build_dimensions(main_records, raw_records)
        val_to_id = {
            "board": board_val_to_id,
            "market": market_val_to_id,
            "industry": industry_val_to_id,
        }
        if val_to_id and list_svc.industry_map_model and list_svc.board_map_model and list_svc.market_map_model:
            save_stock_dimension_mappings(
                dimensions, val_to_id,
                list_svc.industry_map_model,
                list_svc.board_map_model,
                list_svc.market_map_model,
            )

        # 使用本批次时间戳更新缓存
        try:
            dm.db_cache.save(CACHE_KEY, json={CACHE_DATE_FIELD: time_str})
        except Exception:
            pass

        return {"data": main_records}

    # ---------- 私有：钩子内步骤 ----------

    def _is_valid_cache(self, cache: Optional[Dict[str, Any]]) -> bool:
        if not cache:
            return False
        cache_date = cache.get(CACHE_DATE_FIELD)
        if not cache_date:
            return False
        return DateUtils.is_today(cache_date)

    def _group_boards_markets_and_industries(self, raw_records: List[Dict[str, Any]]) -> Tuple[List[str], List[str], List[str]]:
        """从 raw_records 提取去重后的 board/market/industry 值列表。有则参与归类，无则不计入。"""
        boards: Set[str] = set()
        markets: Set[str] = set()
        industries: Set[str] = set()
        for record in raw_records:
            v = (record.get("board") or "").strip()
            if v:
                boards.add(v)
            v = (record.get("market") or "").strip()
            if v:
                markets.add(v)
            v = (record.get("industry") or "").strip()
            if v:
                industries.add(v)
        return list(boards), list(markets), list(industries)

    def _build_dimensions(
        self, main_records: List[Dict[str, Any]], raw_records: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, str, str]]:
        """构建 dimensions: [(stock_id, industry_val, board_val, market_val), ...]。空值传空串，映射时跳过。"""
        dimensions: List[Tuple[str, str, str, str]] = []
        for i, r in enumerate(main_records):
            stock_id = str(r.get("id") or "")
            raw = raw_records[i] if i < len(raw_records) else {}
            industry = (raw.get("industry") or "").strip()
            board = (raw.get("board") or "").strip()
            market = (raw.get("market") or "").strip()
            dimensions.append((stock_id, industry, board, market))
        return dimensions

    def _format_and_store_raw_records(
        self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        formatted = format_mapped_records_with_defaults(mapped_records)
        context["_stock_list_raw_records"] = formatted
        return formatted
