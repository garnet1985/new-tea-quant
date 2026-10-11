"""申万 2021 分类、成分和一级行业日线。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .. import BaseDataService
from core.infra.utils import Utils

# 申万 A 指不在分类树里，但日线表把它和一级行业放在一起。
SW_A_SHARE_ID = "801003.SI"
SW_A_SHARE_NAME = "申万A指"


class SwIndustryService(BaseDataService):
    """读取 sys_sw_industry / sys_sw_stock_industry_map / sys_sw_industry_kline。"""

    def __init__(self, data_manager: Any) -> None:
        super().__init__(data_manager)
        self._industry = data_manager.get_table("sys_sw_industry")
        self._stock_map = data_manager.get_table("sys_sw_stock_industry_map")
        self._kline = data_manager.get_table("sys_sw_industry_kline")

    def load_tree(self) -> List[Dict[str, Any]]:
        """分类树，含一、二、三级。"""
        if not self._industry:
            return []
        return self._industry.load("1=1", order_by="level ASC, industry_code ASC") or []

    def load_quote_list(self) -> List[Dict[str, Any]]:
        """有日线的实体：一级行业，外加申万 A 指。"""
        rows = []
        if self._industry:
            rows = self._industry.load("level = %s", ("L1",), order_by="id ASC") or []
        out: List[Dict[str, Any]] = []
        seen = set()
        for row in rows:
            eid = str(row.get("id") or "").strip()
            if not eid or eid in seen:
                continue
            seen.add(eid)
            out.append(row)
        if SW_A_SHARE_ID not in seen:
            out.append(
                {
                    "id": SW_A_SHARE_ID,
                    "industry_code": "",
                    "name": SW_A_SHARE_NAME,
                    "level": "",
                    "parent_code": "",
                    "is_pub": 1,
                    "src": "SW2021",
                }
            )
        return out

    def load_stock_industry(self, stock_id: str) -> List[Dict[str, Any]]:
        """一只股票当前的一、二、三级。没有成分时返回空列表。"""
        sid = str(stock_id or "").strip()
        if not sid:
            return []
        grouped = self.load_stock_industry_batch([sid])
        return grouped.get(sid, [])

    def load_stock_industry_batch(
        self,
        stock_ids: Sequence[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        ids = [str(sid).strip() for sid in stock_ids if str(sid).strip()]
        result: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in ids}
        if not ids or not self._stock_map:
            return result
        placeholders = ",".join(["%s"] * len(ids))
        rows = self._stock_map.load(
            f"stock_id IN ({placeholders})",
            tuple(ids),
        ) or []
        names = self._industry_names()
        for row in rows:
            sid = str(row.get("stock_id") or "").strip()
            if sid in result:
                result[sid] = [self._with_names(row, names)]
        return result

    def load_kline(
        self,
        industry_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        eid = str(industry_id or "").strip()
        if not eid:
            return []
        grouped = self.load_kline_batch([eid], start_date=start_date, end_date=end_date)
        return grouped.get(eid, [])

    def load_kline_batch(
        self,
        industry_ids: Sequence[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        ids = [str(eid).strip() for eid in industry_ids if str(eid).strip()]
        result: Dict[str, List[Dict[str, Any]]] = {eid: [] for eid in ids}
        if not ids or not self._kline:
            return result
        placeholders = ",".join(["%s"] * len(ids))
        conditions = [f"id IN ({placeholders})"]
        params: List[Any] = list(ids)
        start = Utils.date.normalize(start_date, fmt=Utils.date.FMT_YYYYMMDD) if start_date else None
        end = Utils.date.normalize(end_date, fmt=Utils.date.FMT_YYYYMMDD) if end_date else None
        if start:
            conditions.append("date >= %s")
            params.append(start)
        if end:
            conditions.append("date <= %s")
            params.append(end)
        rows = self._kline.load(
            " AND ".join(conditions),
            tuple(params),
            order_by="id ASC, date ASC",
        ) or []
        for row in rows:
            eid = str(row.get("id") or "").strip()
            if eid in result:
                result[eid].append(row)
        return result

    def _industry_names(self) -> Dict[str, str]:
        if not self._industry:
            return {}
        rows = self._industry.load("1=1") or []
        return {
            str(row.get("id")): str(row.get("name") or "")
            for row in rows
            if row.get("id")
        }

    @staticmethod
    def _with_names(row: Dict[str, Any], names: Dict[str, str]) -> Dict[str, Any]:
        l1 = str(row.get("l1_code") or "")
        l2 = str(row.get("l2_code") or "")
        l3 = str(row.get("l3_code") or "")
        return {
            "stock_id": row.get("stock_id"),
            "l1_code": l1,
            "l1_name": names.get(l1, ""),
            "l2_code": l2,
            "l2_name": names.get(l2, ""),
            "l3_code": l3,
            "l3_name": names.get(l3, ""),
            "in_date": row.get("in_date") or "",
        }
