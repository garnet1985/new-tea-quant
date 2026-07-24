"""slice_based 回测窗开市日解析。

本文件:
- BacktestCalendarResolver: DataManager 日历 → open_dates + backtest_calendar dict
  边界: 负责日历加载与区间过滤；不负责 job payload 其它字段或 BE 执行
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from core.modules.data_manager import DataManager
from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper

logger = logging.getLogger(__name__)


class BacktestCalendarResolver:
    """加载回测窗开市日，供 slice_based dispatch job 使用。

    边界:
    - 负责: 解析 market 日历 → open_dates + backtest_calendar dict
    - 不负责: job payload 其它字段、执行
    - 调用方: slice_based.JobBuilder
    """

    _DEFAULT_MARKET = "SSE"
    _DEFAULT_MARKET_PROFILE = "china_a_stock"

    @classmethod
    def resolve(
        cls,
        *,
        settings: Dict[str, Any],
        start_date: str,
        end_date: str,
        data_manager: Any = None,
    ) -> Tuple[List[str], Dict[str, Any]]:
        calendar_dict = cls.build_calendar_dict(
            settings=settings,
            start_date=start_date,
            end_date=end_date,
            data_manager=data_manager,
        )
        open_dates = CalendarOpenDateHelper.filter_in_range(
            list(calendar_dict.get("open_dates") or []),
            start_date,
            end_date,
        )
        if not open_dates:
            raise ValueError(
                f"回测窗 {start_date}—{end_date} 无开市日，请先 renew trade_calendar"
            )
        calendar_dict = {
            **calendar_dict,
            "period_start": start_date,
            "period_end": end_date,
            "open_dates": open_dates,
        }
        return open_dates, calendar_dict

    @classmethod
    def build_calendar_dict(
        cls,
        *,
        settings: Dict[str, Any],
        start_date: str,
        end_date: str,
        data_manager: Any = None,
    ) -> Dict[str, Any]:
        start = str(start_date or "").strip()
        end = str(end_date or "").strip()
        if not start or not end:
            raise ValueError("start_date / end_date 不能为空")

        market_profile = str(settings.get("market_profile") or cls._DEFAULT_MARKET_PROFILE).strip()
        market = cls._market_for_profile(market_profile)

        dm = data_manager or DataManager(is_verbose=False)
        cal_svc = cls._calendar_service(dm)
        if cal_svc is None:
            raise ValueError("DataManager 无 CalendarService，无法加载开市日")

        raw_dates = cal_svc.load_open_dates(start, end, market=market)
        open_dates = sorted({str(d).strip() for d in raw_dates if str(d).strip()})
        if not open_dates:
            raise ValueError(
                f"回测窗 {start}—{end} 在 sys_trade_calendar（market={market}）无开市日"
            )

        return {
            "market": market,
            "period_start": start,
            "period_end": end,
            "open_dates": open_dates,
        }

    @classmethod
    def filter_in_range(
        cls,
        open_dates: List[str],
        start_date: str,
        end_date: str,
    ) -> List[str]:
        return CalendarOpenDateHelper.filter_in_range(open_dates, start_date, end_date)

    @classmethod
    def _market_for_profile(cls, market_profile_id: str) -> str:
        _ = str(market_profile_id or "").strip() or cls._DEFAULT_MARKET_PROFILE
        return cls._DEFAULT_MARKET

    @staticmethod
    def _calendar_service(data_manager: Any) -> Any:
        if hasattr(data_manager, "service"):
            return data_manager.service.calendar
        if hasattr(data_manager, "calendar"):
            return data_manager.calendar
        return None


__all__ = ["BacktestCalendarResolver"]
