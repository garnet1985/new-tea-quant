"""
真实世界最新已完成交易日（网络侧探测）。

由 DataSource 提供 HTTP/Provider 能力；DataManager.CalendarService 经注入回调使用，
避免 DM → DS 模块依赖。
"""
from __future__ import annotations
from core.infra.cmd_layout import i

import logging
from typing import Optional, Sequence, Tuple

from core.infra.utils import Utils
from core.modules.data_source.core.service.provider_helper import DataSourceProviderHelper

logger = logging.getLogger(__name__)


def fetch_real_world_latest_completed_trading_date() -> Optional[Tuple[str, str]]:
    """
    用 AKShare 的腾讯指数日线探测。成功返回 ``(YYYYMMDD, provider)``，失败返回 ``None``。

    不含周末猜测兜底（由 CalendarService 负责）。
    """
    latest = _try_fetch("腾讯财经", _fetch_from_akshare)
    if latest:
        return latest, "akshare"
    return None


def _try_fetch(provider_name: str, fetch_func) -> Optional[str]:
    today = Utils.date.today()
    try:
        latest_date = fetch_func()
        if latest_date and latest_date != today:
            logger.info(i('success') + " 从%sAPI获取最新交易日: %s", provider_name, latest_date)
            return latest_date
    except Exception as e:
        logger.warning(i('warning') + "  %sAPI失败: %s", provider_name, e)
    return None


def _fetch_from_akshare() -> Optional[str]:
    try:
        provider = DataSourceProviderHelper.get_provider("akshare")
        if not provider:
            raise ValueError("AKShare Provider 未找到")
        today = Utils.date.today()
        start = Utils.date.add_days(today, -20)
        frame = provider.get_qfq_kline(
            symbol="sh000001",
            start_date=start,
            end_date=today,
            adjust="",
        )
        dates = _dates_from_frame(frame)
        if not dates:
            raise ValueError("未获取到K线数据")
        return _latest_completed(dates)
    except Exception as e:
        logger.error(i('error') + " 从腾讯财经获取最新交易日失败: %s", e)
        raise


def _dates_from_frame(frame) -> list:
    if frame is None:
        return []
    column = frame["date"] if hasattr(frame, "__getitem__") else None
    if column is None:
        return []
    dates = []
    for value in list(column):
        text = str(value)[:10]
        if text and text != "NaT":
            dates.append(Utils.date.normalize_str(text))
    return dates


def _latest_completed(dates: Sequence[str]) -> str:
    today = Utils.date.today()
    last = dates[-1]
    if last == today and len(dates) >= 2:
        return dates[-2]
    return last
