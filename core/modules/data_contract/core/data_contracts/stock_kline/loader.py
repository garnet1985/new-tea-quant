"""StockKline Loader。"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager
from core.infra.utils import Utils
class StockKlineLoader(BaseDataContractLoader):
    """Unified loader for stock kline (qfq/nfq)."""

    @staticmethod
    def _load_by_adjust(
        *,
        kline_service: Any,
        stock_id: str,
        term: str,
        start: Optional[str],
        end: Optional[str],
        adjust: str,
    ) -> List[Mapping[str, Any]]:
        """根据复权类型加载 K 线数据。"""
        if adjust == "qfq":
            return kline_service.load_qfq_split(
                stock_id=stock_id, term=term, start_date=start, end_date=end
            )
        if adjust in ("nfq", "none"):
            return kline_service.load_raw(stock_id=stock_id, term=term, start_date=start, end_date=end)
        raise ValueError(f"加载 stock.kline 失败：不支持 adjust={adjust!r}，仅支持 qfq/nfq/none")

    def load(self, params: Mapping[str, Any]) -> Any:
        data_mgr = DataManager()
        kline_service = data_mgr.stock.kline

        # 从 params 获取 stock_id
        stock_id = params.get("stock_id") or params.get("id") or params.get("entity_id")
        if not stock_id:
            raise ValueError("加载 stock.kline 失败：缺少 stock_id（请在 params 中提供 stock_id/id/entity_id）")
        stock_id = str(stock_id).strip()

        term = str(params.get("term", "daily"))
        adjust = str(params.get("adjust", "qfq")).lower()

        start = Utils.date.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = Utils.date.normalize_str(params.get("end")) if params.get("end") is not None else None
        amount = params.get("amount")
        direction = int(params.get("direction", -1))
        include_boundary = bool(params.get("include_boundary", True))

        if amount is not None:
            if not isinstance(amount, int):
                raise TypeError("加载 stock.kline 失败：amount 必须是 int")
            if amount < 1:
                raise ValueError("加载 stock.kline 失败：amount 必须 >= 1")
        if direction not in (-1, 1):
            raise ValueError("加载 stock.kline 失败：direction 只能是 -1 或 1")
        if start is None and end is not None:
            raise ValueError("加载 stock.kline 失败：仅传 end 无效，需同时传 start")
        if end is not None and amount is not None:
            raise ValueError("加载 stock.kline 失败：end 与 amount 不能同时传入")

        # all
        if start is None and end is None and amount is None:
            return self._load_by_adjust(
                kline_service=kline_service,
                stock_id=stock_id,
                term=term,
                start=None,
                end=None,
                adjust=adjust,
            )

        # range
        if start is not None and end is not None:
            left, right = (start, end) if start <= end else (end, start)
            rows = self._load_by_adjust(
                kline_service=kline_service,
                stock_id=stock_id,
                term=term,
                start=left,
                end=right,
                adjust=adjust,
            )
            return self.drop_boundary_rows(rows, start=left, end=right, include_boundary=include_boundary)

        # point / lookback / lookforward
        if start is None:
            raise ValueError("加载 stock.kline 失败：仅传 amount/direction 无效，需同时传 start")

        normalized_amount = amount if amount is not None else 1
        if direction == -1:
            rows = self._load_by_adjust(
                kline_service=kline_service,
                stock_id=stock_id,
                term=term,
                start=None,
                end=start,
                adjust=adjust,
            )
            rows = self.drop_boundary_rows(rows, start=None, end=start, include_boundary=include_boundary)
            return rows[-normalized_amount:]

        rows = self._load_by_adjust(
            kline_service=kline_service,
            stock_id=stock_id,
            term=term,
            start=start,
            end=None,
            adjust=adjust,
        )
        rows = self.drop_boundary_rows(rows, start=start, end=None, include_boundary=include_boundary)
        return rows[:normalized_amount]

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ids = [str(x).strip() for x in entity_ids if str(x).strip()]
        if not ids:
            return {}

        data_mgr = DataManager()
        kline_service = data_mgr.stock.kline

        term = str(params.get("term", "daily"))
        adjust = str(params.get("adjust", "qfq")).lower()
        start = Utils.date.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = Utils.date.normalize_str(params.get("end")) if params.get("end") is not None else None
        include_boundary = bool(params.get("include_boundary", True))

        if adjust not in ("qfq", "nfq", "none"):
            raise ValueError(f"加载 stock.kline 失败：不支持 adjust={adjust!r}，仅支持 qfq/nfq/none")

        amount = params.get("amount")
        if amount is not None or (start is not None and end is None) or (start is None and end is not None):
            # 使用基类的默认实现：循环调用 load()
            result = {}
            for eid in ids:
                single_params = self.build_batch_load_params(eid, params)
                result[eid] = self.load(single_params)
            return result

        if start is not None and end is not None:
            left, right = (start, end) if start <= end else (end, start)
            raw_by_entity = kline_service.load_batch(
                ids,
                term=term,
                start_date=left,
                end_date=right,
                adjust=adjust,
            )
            if include_boundary:
                return raw_by_entity
            return {
                eid: self.drop_boundary_rows(
                    list(raw_by_entity.get(eid) or []),
                    start=left,
                    end=right,
                    include_boundary=False,
                )
                for eid in ids
            }

        return kline_service.load_batch(
            ids,
            term=term,
            start_date=None,
            end_date=None,
            adjust=adjust,
        )