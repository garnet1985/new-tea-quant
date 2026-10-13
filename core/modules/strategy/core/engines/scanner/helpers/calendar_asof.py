"""Scanner 横截面预筛：有 ``on_calendar_slice`` 时先选股再扫。

本文件:
- ScannerCalendarAsof: 主进程调用切片钩子，收窄 ``stock_ids``
  边界: 负责预筛；不负责 BE job / is_opportunity
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Sequence

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper
from core.modules.strategy.core.hooks.hook_params import CalendarSlice, open_context
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)

_DATA_KEY_DAILY = "stock.kline.daily"


class ScannerCalendarAsof:
    """横截面策略扫描前：用 ``on_calendar_slice`` 替换全市场 ``stock_ids``。"""

    @classmethod
    def filter_stock_ids(
        cls,
        *,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        stock_ids: Sequence[str],
        scan_date: str,
        data_manager: Any,
    ) -> List[str]:
        ids = [str(sid).strip() for sid in stock_ids if str(sid).strip()]
        day = str(scan_date or "").strip()
        if not ids or not day:
            return ids

        hook_runtime, err = StrategyHookRuntime.from_strategy_info(strategy_info, settings)
        if hook_runtime is None:
            logger.warning("scanner calendar asof 跳过：hooks 加载失败 %s", err)
            return ids
        if not hook_runtime.is_overridden("on_calendar_slice"):
            return ids

        open_dates = cls._load_open_dates(data_manager, day)
        if not open_dates or day not in open_dates:
            logger.warning(
                "scanner calendar asof：scan_date=%s 不在开市日轴上，保持原宇宙 size=%d",
                day,
                len(ids),
            )
            return ids

        period = cls._resolve_rebalance_period(settings)
        index = open_dates.index(day)
        calendar = cls._build_calendar_view(
            day,
            open_dates,
            rebalance_period=period,
            open_date_index=index,
        )

        strategy_key = str(
            getattr(strategy_info, "key", None)
            or getattr(strategy_info, "unique_relative_path", "")
            or ""
        ).strip()
        ctx = open_context(
            strategy_key=strategy_key,
            settings=settings,
            sample_list=ids,
        )
        base_key = str(getattr(settings.data, "base_data_key", None) or _DATA_KEY_DAILY).strip()
        calendar_slice = CalendarSlice(
            flags=calendar,
            base_data_key=base_key or _DATA_KEY_DAILY,
            loader=lambda: cls._load_by_entity(
                data_manager,
                settings=settings,
                stock_ids=ids,
                scan_date=day,
            ),
        )
        try:
            result = hook_runtime.call("on_calendar_slice", ctx, calendar_slice)
        except Exception as exc:
            logger.error("scanner on_calendar_slice 失败: %s", exc, exc_info=True)
            return ids

        allowed = set(ids)
        selected = [
            str(sid).strip()
            for sid in (result or [])
            if str(sid).strip() in allowed
        ]
        logger.info(
            "scanner calendar asof: date=%s period=%s universe=%d -> selected=%d",
            day,
            period,
            len(ids),
            len(selected),
        )
        return selected

    @staticmethod
    def _resolve_rebalance_period(settings: StrategySettings) -> str:
        core = settings.raw_settings.get("core")
        if not isinstance(core, dict):
            return "year"
        period = str(core.get("rebalance_period") or "year").strip().lower()
        return period if period in {"month", "year"} else "year"

    @staticmethod
    def _load_open_dates(data_manager: Any, scan_date: str) -> List[str]:
        day = str(scan_date or "").strip()
        if len(day) < 4:
            return []
        try:
            year = int(day[:4])
        except ValueError:
            return []
        cal_svc = getattr(getattr(data_manager, "service", None), "calendar", None)
        if cal_svc is None or not callable(getattr(cal_svc, "load_open_dates", None)):
            return []
        start = f"{year - 1}0101"
        end = f"{year + 1}1231"
        try:
            rows = cal_svc.load_open_dates(start, end, market="SSE")
        except Exception as exc:
            logger.debug("load_open_dates failed: %s", exc)
            return []
        return [str(d).strip() for d in (rows or []) if str(d).strip()]

    @staticmethod
    def _build_calendar_view(
        as_of: str,
        open_dates: Sequence[str],
        *,
        rebalance_period: str,
        open_date_index: int,
    ) -> Dict[str, Any]:
        all_open = list(open_dates)
        if rebalance_period == "month":
            is_period_start = CalendarOpenDateHelper.is_first_open_of_month(as_of, all_open)
            is_period_end = CalendarOpenDateHelper.is_last_open_of_month(as_of, all_open)
        else:
            is_period_start = CalendarOpenDateHelper.is_first_open_of_year(as_of, all_open)
            is_period_end = CalendarOpenDateHelper.is_last_open_of_year(as_of, all_open)
        return {
            "as_of_date": as_of,
            "open_date_index": open_date_index,
            "is_period_start": is_period_start,
            "is_period_end": is_period_end,
            "is_first_open_of_month": CalendarOpenDateHelper.is_first_open_of_month(
                as_of, all_open
            ),
            "is_last_open_of_month": CalendarOpenDateHelper.is_last_open_of_month(
                as_of, all_open
            ),
            "is_first_open_of_year": CalendarOpenDateHelper.is_first_open_of_year(
                as_of, all_open
            ),
            "is_last_open_of_year": CalendarOpenDateHelper.is_last_open_of_year(
                as_of, all_open
            ),
        }

    @classmethod
    def _load_by_entity(
        cls,
        data_manager: Any,
        *,
        settings: StrategySettings,
        stock_ids: Sequence[str],
        scan_date: str,
    ) -> Dict[str, Dict[str, Any]]:
        """为 asof 选股装当日 K 线（含 ``klines`` 别名）。"""
        ids = [str(sid).strip() for sid in stock_ids if str(sid).strip()]
        day = str(scan_date or "").strip()
        if not ids or not day:
            return {}

        # 单日选股只需要当日 bar；多取几天容错停牌空洞
        start = cls._lookback_start(day, 5)
        kline = getattr(getattr(data_manager, "stock", None), "kline", None)
        loader = getattr(kline, "load_batch", None)
        if not callable(loader):
            logger.warning("scanner asof：DataManager.stock.kline.load_batch 不可用")
            return {}

        try:
            batch = loader(
                list(ids),
                term="daily",
                start_date=start,
                end_date=day,
            )
        except Exception as exc:
            logger.error("scanner asof load_batch 失败: %s", exc, exc_info=True)
            return {}

        base_key = str(
            getattr(settings.data, "base_data_key", None) or _DATA_KEY_DAILY
        ).strip() or _DATA_KEY_DAILY
        out: Dict[str, Dict[str, Any]] = {}
        for eid, rows in (batch or {}).items():
            if not isinstance(rows, list) or not rows:
                continue
            packed = {base_key: rows, "klines": rows}
            out[str(eid)] = packed
        return out

    @staticmethod
    def _lookback_start(scan_date: str, lookback_days: int) -> str:
        day = str(scan_date or "").strip()
        try:
            dt = datetime.strptime(day, "%Y%m%d")
        except ValueError:
            return day
        return (dt - timedelta(days=max(1, int(lookback_days)))).strftime("%Y%m%d")


__all__ = ["ScannerCalendarAsof"]
