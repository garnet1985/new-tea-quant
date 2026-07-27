"""
股票列表服务（ListService）

固定 API（筛选由 Tag 等上层负责）：
- load_single / load_meta：单股
- load_all：全表
- load_listed / load_delisted / load_suspended：按 list_status 快照
- load(*, ...)：仅关键字参数；集合查询（回测窗口 / 时点 / 维度 / status）
- load_by_*：维度查询糖方法（内部调用 load）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union
import logging

from ... import BaseDataService


logger = logging.getLogger(__name__)

_LIST_STATUS_LISTED = "L"
_LIST_STATUS_DELISTED = "D"
_LIST_STATUS_SUSPENDED = "P"

# Tushare 等源对「未退市」常写入 0 / 0.0，须视为无退市日（否则 PIT 会漏掉全体 L 股）
_PIT_DELIST_EMPTY_SQL = (
    "delist_date IS NULL OR delist_date = '' "
    "OR delist_date IN ('0', '0.0')"
)
_PERIOD_WHERE = f"list_date <= %s AND ({_PIT_DELIST_EMPTY_SQL} OR delist_date > %s)"

SURVIVORSHIP_PIT = "pit"
SURVIVORSHIP_SURVIVOR = "survivor"


class ListService(BaseDataService):
    """股票列表服务"""

    def __init__(self, data_manager: Any):
        super().__init__(data_manager)

        self._stock_list = data_manager.get_table("sys_stock_list")
        self._industries = data_manager.get_table("sys_industries")
        self._boards = data_manager.get_table("sys_boards")
        self._markets = data_manager.get_table("sys_markets")
        self._areas = data_manager.get_table("sys_areas")
        self._industry_map = data_manager.get_table("sys_stock_industry_map")
        self._board_map = data_manager.get_table("sys_stock_board_map")
        self._market_map = data_manager.get_table("sys_stock_market_map")
        self._area_map = data_manager.get_table("sys_stock_area_map")

    @property
    def industries_model(self):
        return self._industries

    @property
    def boards_model(self):
        return self._boards

    @property
    def markets_model(self):
        return self._markets

    @property
    def areas_model(self):
        return self._areas

    @property
    def industry_map_model(self):
        return self._industry_map

    @property
    def board_map_model(self):
        return self._board_map

    @property
    def market_map_model(self):
        return self._market_map

    @property
    def area_map_model(self):
        return self._area_map

    # ---------- 单股 ----------

    def load_single(self, stock_id: str) -> Optional[Dict[str, Any]]:
        row = self._stock_list.load_by_id(stock_id)
        if not row:
            return None
        filtered = self._apply_sample_pool([row])
        return filtered[0] if filtered else None

    def load_meta(self, stock_id: str) -> Optional[Dict[str, Any]]:
        row = self.load_single(stock_id)
        if not row:
            return None
        # 出口即清洗：0 / 0.0 占位符 → 空，避免策略侧误判已退市
        delist = self._normalize_delist_date(row.get("delist_date"))
        return {
            "id": row.get("id"),
            "name": row.get("name"),
            "list_status": row.get("list_status"),
            "list_date": row.get("list_date"),
            "delist_date": delist or "",
        }

    # ---------- 全表 / 按 status ----------

    def load_all(self, order_by: str = "id") -> List[Dict[str, Any]]:
        return self._sort_stocks(self._stock_list.load_all_stocks(), order_by)

    def load_listed(self, order_by: str = "id") -> List[Dict[str, Any]]:
        return self.load(list_status=_LIST_STATUS_LISTED, order_by=order_by)

    def load_delisted(self, order_by: str = "id") -> List[Dict[str, Any]]:
        return self.load(list_status=_LIST_STATUS_DELISTED, order_by=order_by)

    def load_suspended(self, order_by: str = "id") -> List[Dict[str, Any]]:
        return self.load(list_status=_LIST_STATUS_SUSPENDED, order_by=order_by)

    # ---------- 统一集合入口（仅关键字参数）----------

    def load(
        self,
        *,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        survivorship: Optional[str] = None,
        as_of_date: Optional[str] = None,
        list_status: Optional[Union[str, Sequence[str]]] = None,
        industry: Optional[Union[str, int]] = None,
        board: Optional[Union[str, int]] = None,
        market: Optional[Union[str, int]] = None,
        area: Optional[Union[str, int]] = None,
        order_by: str = "id",
    ) -> List[Dict[str, Any]]:
        """
        加载股票集合。查询模式互斥，优先级：
        period_start+period_end > as_of_date > 维度 > list_status > load_all。

        period（回测窗口参与者，``survivorship`` 控制退市边界）::

            pit（默认）::
                list_date <= period_end
                AND (无退市日 sentinel 或 delist_date > period_start)

            survivor（幸存者偏差演示）::
                list_date <= period_end
                AND (无退市日 sentinel 或 delist_date > period_end)

        as_of_date（某日仍在市）::
            list_date <= as_of_date
            AND (无退市日 sentinel 或 delist_date > as_of_date)
        """
        if period_start is not None or period_end is not None:
            if not period_start or not period_end:
                raise ValueError("period_start 与 period_end 须同时提供")
            if as_of_date:
                raise ValueError("period_* 与 as_of_date 不能同时使用")
            rows = self._stock_list.load(
                _PERIOD_WHERE,
                self._period_where_params(
                    period_start=period_start,
                    period_end=period_end,
                    survivorship=survivorship,
                ),
                order_by=f"{order_by} ASC",
            )
            return self._sort_stocks(rows, order_by)

        if as_of_date:
            rows = self._stock_list.load(
                _PERIOD_WHERE,
                (as_of_date, as_of_date),
                order_by=f"{order_by} ASC",
            )
            return self._sort_stocks(rows, order_by)

        if industry is not None:
            return self._load_by_dimension("industry", industry, order_by)
        if board is not None:
            return self._load_by_dimension("board", board, order_by)
        if market is not None:
            return self._load_by_dimension("market", market, order_by)
        if area is not None:
            return self._load_by_dimension("area", area, order_by)

        if list_status is not None:
            statuses = (
                [list_status]
                if isinstance(list_status, str)
                else [str(s) for s in list_status if s]
            )
            if not statuses:
                return []
            placeholders = ",".join(["%s"] * len(statuses))
            rows = self._stock_list.load(
                f"list_status IN ({placeholders})",
                tuple(statuses),
                order_by=f"{order_by} ASC",
            )
            return self._sort_stocks(rows, order_by)

        return self.load_all(order_by=order_by)

    def load_by_industry(
        self,
        industry: Union[str, int],
        order_by: str = "id",
    ) -> List[Dict[str, Any]]:
        return self.load(industry=industry, order_by=order_by)

    def load_by_board(
        self,
        board: Union[str, int],
        order_by: str = "id",
    ) -> List[Dict[str, Any]]:
        return self.load(board=board, order_by=order_by)

    def load_by_market(
        self,
        market: Union[str, int],
        order_by: str = "id",
    ) -> List[Dict[str, Any]]:
        return self.load(market=market, order_by=order_by)

    def load_by_area(
        self,
        area: Union[str, int],
        order_by: str = "id",
    ) -> List[Dict[str, Any]]:
        return self.load(area=area, order_by=order_by)

    @staticmethod
    def normalize_survivorship(raw: Any) -> str:
        mode = str(raw or SURVIVORSHIP_PIT).strip().lower()
        if mode in (SURVIVORSHIP_PIT, SURVIVORSHIP_SURVIVOR):
            return mode
        return SURVIVORSHIP_PIT

    @classmethod
    def _period_where_params(
        cls,
        *,
        period_start: str,
        period_end: str,
        survivorship: Optional[str],
    ) -> tuple[str, str]:
        mode = cls.normalize_survivorship(survivorship)
        if mode == SURVIVORSHIP_SURVIVOR:
            return (period_end, period_end)
        return (period_end, period_start)

    @staticmethod
    def _normalize_delist_date(raw: Any) -> Optional[str]:
        """将源数据中的占位退市日（0 / 0.0）视为未退市。"""
        s = str(raw or "").strip()
        if not s or s.lower() in ("none", "nan", "0", "0.0"):
            return None
        return s

    @staticmethod
    def is_tradable_on(stock: Dict[str, Any], trade_date: str) -> bool:
        """模拟日是否可交易（资格层；执行层仍以 K 线是否存在为准）。"""
        listed = str(stock.get("list_date") or "").strip()
        if listed and trade_date < listed:
            return False
        delisted = ListService._normalize_delist_date(stock.get("delist_date"))
        if delisted and trade_date >= delisted:
            return False
        return True

    def save(self, stocks: List[Dict[str, Any]]) -> int:
        return self._stock_list.save_stocks(stocks)

    def ensure_and_sync_industries(self, values: List[str]) -> Dict[str, int]:
        return self._ensure_and_sync_dimension_batch(self._industries, values) if self._industries else {}

    def ensure_and_sync_boards(self, values: List[str]) -> Dict[str, int]:
        return self._ensure_and_sync_dimension_batch(self._boards, values) if self._boards else {}

    def ensure_and_sync_markets(self, values: List[str]) -> Dict[str, int]:
        return self._ensure_and_sync_market_batch(self._markets, values) if self._markets else {}

    def ensure_and_sync_areas(self, values: List[str]) -> Dict[str, int]:
        return self._ensure_and_sync_dimension_batch(self._areas, values) if self._areas else {}

    def _load_by_dimension(
        self,
        dimension: str,
        value: Union[str, int],
        order_by: str,
    ) -> List[Dict[str, Any]]:
        resolvers = {
            "industry": (self._resolve_industry_id, self._industry_map, "industry_id"),
            "board": (self._resolve_board_id, self._board_map, "board_id"),
            "market": (self._resolve_market_id, self._market_map, "market_id"),
            "area": (self._resolve_area_id, self._area_map, "area_id"),
        }
        resolve_id, map_model, id_column = resolvers[dimension]
        dim_id = resolve_id(value)
        if dim_id is None or not map_model:
            return []
        return self._load_stocks_by_map(map_model, id_column, dim_id, order_by)

    def _load_stocks_by_map(
        self,
        map_model,
        id_column: str,
        dimension_id: int,
        order_by: str,
    ) -> List[Dict[str, Any]]:
        map_rows = map_model.load(f"{id_column} = %s", (dimension_id,))
        stock_ids = [r["stock_id"] for r in map_rows if r.get("stock_id")]
        if not stock_ids:
            return []
        placeholders = ",".join(["%s"] * len(stock_ids))
        stocks = self._stock_list.load(
            f"id IN ({placeholders})",
            tuple(stock_ids),
            order_by=f"{order_by} ASC",
        )
        return self._sort_stocks(stocks, order_by)

    def _resolve_industry_id(self, industry: Union[str, int]) -> Optional[int]:
        if isinstance(industry, int):
            return industry
        row = self._industries.load_one("value = %s", (industry,)) if self._industries else None
        return int(row["id"]) if row and row.get("id") is not None else None

    def _resolve_board_id(self, board: Union[str, int]) -> Optional[int]:
        if isinstance(board, int):
            return board
        row = self._boards.load_one("value = %s", (board,)) if self._boards else None
        return int(row["id"]) if row and row.get("id") is not None else None

    def _resolve_market_id(self, market: Union[str, int]) -> Optional[int]:
        if isinstance(market, int):
            return market
        row = self._markets.load_one("value = %s", (market,)) if self._markets else None
        if row and row.get("id") is not None:
            return int(row["id"])
        if self._markets:
            row = self._markets.load_one("code = %s", (market,))
            if row and row.get("id") is not None:
                return int(row["id"])
        return None

    def _resolve_area_id(self, area: Union[str, int]) -> Optional[int]:
        if isinstance(area, int):
            return area
        row = self._areas.load_one("value = %s", (area,)) if self._areas else None
        return int(row["id"]) if row and row.get("id") is not None else None

    def _ensure_and_sync_dimension_batch(
        self,
        model,
        current_values: List[str],
        value_col: str = "value",
    ) -> Dict[str, int]:
        if not model or not current_values:
            if model:
                self._sync_dimension_alive(model, [], value_col)
            return {}

        vals = tuple(current_values)
        # 勿用双引号包列名：MySQL 默认把 "value" 当字符串字面量，导致 IN 永远匹配不到行
        existing = model.load(f"{value_col} IN %s", (vals,))
        val_to_id: Dict[str, int] = {
            row[value_col]: int(row["id"])
            for row in existing
            if row.get(value_col) and row.get("id") is not None
        }
        new_values = [v for v in current_values if v not in val_to_id]

        if new_values:
            rows = [{"value": v, "is_alive": 1} for v in new_values]
            model.insert_many(rows)
            new_rows = model.load(f"{value_col} IN %s", (tuple(new_values),))
            for row in new_rows:
                if row.get(value_col) and row.get("id") is not None:
                    val_to_id[row[value_col]] = int(row["id"])

        self._sync_dimension_alive(model, current_values, value_col)
        return {v: val_to_id[v] for v in current_values if v in val_to_id}

    def _ensure_and_sync_market_batch(
        self,
        model,
        current_values: List[str],
    ) -> Dict[str, int]:
        if not model or not current_values:
            if model:
                self._sync_dimension_alive(model, [], "value")
            return {}

        vals = tuple(current_values)
        existing = model.load("value IN %s", (vals,))
        val_to_id: Dict[str, int] = {
            row["value"]: int(row["id"])
            for row in existing
            if row.get("value") and row.get("id") is not None
        }
        new_values = [v for v in current_values if v not in val_to_id]

        if new_values:
            rows = []
            for v in new_values:
                payload: Dict[str, Any] = {"value": v, "is_alive": 1}
                if v in ("SSE", "SZSE", "BSE"):
                    payload["code"] = v
                rows.append(payload)
            model.insert_many(rows)
            new_rows = model.load("value IN %s", (tuple(new_values),))
            for row in new_rows:
                if row.get("value") and row.get("id") is not None:
                    val_to_id[row["value"]] = int(row["id"])

        self._sync_dimension_alive(model, current_values, "value")
        return {v: val_to_id[v] for v in current_values if v in val_to_id}

    def _sync_dimension_alive(
        self, model, current_values: List[str], value_col: str = "value"
    ) -> None:
        try:
            unique_keys = model.get_primary_keys()
        except ValueError:
            return
        if current_values:
            vals = tuple(current_values)
            rows_deactivate = model.load(f"{value_col} NOT IN %s", (vals,))
            if rows_deactivate:
                for r in rows_deactivate:
                    r["is_alive"] = 0
                model.upsert(rows_deactivate, unique_keys)
            rows_activate = model.load(f"{value_col} IN %s", (vals,))
            if rows_activate:
                for r in rows_activate:
                    r["is_alive"] = 1
                model.upsert(rows_activate, unique_keys)
        else:
            rows_all = model.load("1=1")
            if rows_all:
                for r in rows_all:
                    r["is_alive"] = 0
                model.upsert(rows_all, unique_keys)

    @staticmethod
    def _apply_sample_pool(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from core.modules.data_source.service.sample_stock_list import slice_stock_list

        return slice_stock_list(stocks)

    def _sort_stocks(self, stocks: List[Dict[str, Any]], order_by: str) -> List[Dict[str, Any]]:
        if order_by:
            try:
                stocks.sort(key=lambda x: x.get(order_by, ""))
            except Exception as e:
                logger.warning("排序失败，使用默认排序: %s", e)
                stocks.sort(key=lambda x: x.get("id", ""))
        return self._apply_sample_pool(stocks)
