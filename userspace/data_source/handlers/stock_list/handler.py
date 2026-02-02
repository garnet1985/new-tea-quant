"""
股票列表 Handler

使用 Tushare Provider 获取股票列表（包含所有交易所）。
流程：on_before_run 检查 sys_cache -> 若今日已更新则从 DB 返回短路；否则 API -> on_before_save 写维度/映射/cache。
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.utils.date.date_utils import DateUtils, DateFormat

from .helper import (
    format_mapped_records_with_defaults,
    ensure_and_sync_dimension_batch,
    ensure_and_sync_market_batch,
    save_stock_dimension_mappings,
)

CACHE_KEY = "stock_list_last_update"

class TushareStockListHandler(BaseHandler):
    """
    股票列表 Handler

    流程：on_before_run 检查 sys_cache，若今日已更新则从 DB 返回短路；否则 API -> on_before_save 写维度/映射/cache。
    """

    def on_before_run(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """若 sys_cache 记录今日已更新，则从 DB 读取并返回，跳过 API 调用。"""
        dm = context.get("data_manager")
        try:
            cache = dm.db_cache.get(CACHE_KEY)
            if self._is_valid_cache(cache):
                return {"data": dm.stock.list.load_all()}
            return None
        except Exception as e:
            logger.warning(f"检查 stock_list 缓存失败: {e}")
            return None

    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted = self._format_and_store_raw_records(context, mapped_records)
        logger.info(f"✅ 股票列表字段映射完成，共 {len(formatted)} 只股票")
        return formatted

    def on_before_save(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """1. 同步维度表（boards/markets/industries）；2. 写 stock_list；3. 写映射表；4. 写 cache。返回 main_records 供 base 的 _system_save 写入。"""
        dm = context.get("data_manager")
        main_records = (normalized_data or {}).get("data") or []
        if not main_records:
            return {"data": []}

        # save 入口统一打本批次的 last_update 时间戳
        batch_ts = DateUtils.get_current_date_str(DateUtils.DATE_FORMAT_YYYY_MM_DD_HH_MM_SS)
        for r in main_records:
            r["last_update"] = batch_ts

        if not dm or context.get("is_dry_run"):
            return {"data": main_records}

        raw_records = context.get("_stock_list_raw_records") or []
        boards, markets, industries = self._group_boards_markets_and_industries(raw_records)

        board_val_to_id = self._save_boards(dm, boards)
        market_val_to_id = self._save_markets(dm, markets)
        industry_val_to_id = self._save_industries(dm, industries)

        dimensions = self._build_dimensions(main_records, raw_records)
        val_to_id = {
            "board": board_val_to_id,
            "market": market_val_to_id,
            "industry": industry_val_to_id,
        }
        list_svc = dm.stock.list
        if val_to_id and list_svc.industry_map_model and list_svc.board_map_model and list_svc.market_map_model:
            save_stock_dimension_mappings(
                dimensions, val_to_id,
                list_svc.industry_map_model,
                list_svc.board_map_model,
                list_svc.market_map_model,
            )

        # 使用本批次时间戳更新缓存
        if batch_ts and dm.db_cache:
            try:
                dm.db_cache.set(CACHE_KEY, batch_ts)
                logger.info(f"✅ sys_cache 已记录 stock_list_last_update: {batch_ts}")
            except Exception as e:
                logger.warning(f"写入 sys_cache 失败: {e}")

        return {"data": main_records}

    # ---------- 私有：钩子内步骤 ----------

    def _is_valid_cache(self, cache: Dict[str, Any]) -> bool:
        if not cache:
            return False
        last_updated = cache.get("last_updated")
        if not last_updated:
            return False
        cache_date = DateUtils.normalize_to_format(last_updated, DateFormat.DAY)
        return cache_date == DateUtils.get_current_date_str()

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

    def _save_boards(self, dm: Any, boards: List[str]) -> Dict[str, int]:
        """批量确保 sys_boards，1 次 load + 0~1 次 batch_insert + 0~1 次 load + 2 次 update。"""
        model = dm.stock.list.boards_model
        return ensure_and_sync_dimension_batch(model, boards) if model else {}

    def _save_markets(self, dm: Any, markets: List[str]) -> Dict[str, int]:
        """批量确保 sys_markets，同上。"""
        model = dm.stock.list.markets_model
        return ensure_and_sync_market_batch(model, markets) if model else {}

    def _save_industries(self, dm: Any, industries: List[str]) -> Dict[str, int]:
        """批量确保 sys_industries，同上。"""
        model = dm.stock.list.industries_model
        return ensure_and_sync_dimension_batch(model, industries) if model else {}


    def _format_and_store_raw_records(
        self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        formatted = format_mapped_records_with_defaults(mapped_records)
        context["_stock_list_raw_records"] = formatted
        return formatted
