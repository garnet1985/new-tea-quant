"""
真实世界最新已完成交易日（网络侧探测）。

由 DataSource 提供 HTTP/Provider 能力；DataManager.CalendarService 经注入回调使用，
避免 DM → DS 模块依赖。
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from core.infra.utils import Utils
from core.modules.data_source.core.service.provider_helper import DataSourceProviderHelper

logger = logging.getLogger(__name__)


def fetch_real_world_latest_completed_trading_date() -> Optional[Tuple[str, str]]:
    """
    新浪 → 东财；成功返回 ``(YYYYMMDD, provider)``，全部失败返回 ``None``。

    不含周末猜测兜底（由 CalendarService 负责）。
    """
    latest = _try_fetch("新浪财经", _fetch_from_sina)
    if latest:
        return latest, "sina"

    latest = _try_fetch("东方财富", _fetch_from_eastmoney)
    if latest:
        return latest, "eastmoney"

    return None


def _try_fetch(provider_name: str, fetch_func) -> Optional[str]:
    today = Utils.date.today()
    try:
        latest_date = fetch_func()
        if latest_date and latest_date != today:
            logger.info("✅ 从%sAPI获取最新交易日: %s", provider_name, latest_date)
            return latest_date
    except Exception as e:
        logger.warning("⚠️  %sAPI失败: %s", provider_name, e)
    return None


def _fetch_from_eastmoney() -> Optional[str]:
    try:
        provider = DataSourceProviderHelper.get_provider("eastmoney")
        if not provider:
            raise ValueError("EastMoney Provider 未找到")

        result = provider.get_qfq_kline(secid="1.000001", limit=2)
        if not result or "data" not in result:
            raise ValueError("东方财富API返回数据格式错误")

        klines = result.get("data", {}).get("klines", [])
        if not klines or len(klines) < 1:
            raise ValueError("未获取到K线数据")

        return _extract_latest_date_from_klines(klines, is_eastmoney=True)
    except Exception as e:
        logger.error("❌ 从东方财富API获取最新交易日失败: %s", e)
        raise


def _fetch_from_sina() -> Optional[str]:
    try:
        provider = DataSourceProviderHelper.get_provider("sina")
        if not provider:
            raise ValueError("Sina Provider 未找到")

        result = provider.get_daily_kline(symbol="sh000001", datalen=2)
        if not result or "data" not in result:
            raise ValueError("新浪财经API返回数据格式错误")

        klines = result.get("data", [])
        if not klines or len(klines) < 1:
            raise ValueError("未获取到K线数据")

        return _extract_latest_date_from_klines(klines, is_eastmoney=False)
    except Exception as e:
        logger.error("❌ 从新浪财经API获取最新交易日失败: %s", e)
        raise


def _extract_latest_date_from_klines(klines: list, is_eastmoney: bool) -> str:
    last_two = klines[-2:] if len(klines) >= 2 else [klines[-1]]
    today = Utils.date.today()

    last_kline = last_two[-1]
    if is_eastmoney:
        last_date_str = last_kline.split(",")[0]
    else:
        last_date_str = last_kline[0]

    last_date = Utils.date.normalize_str(last_date_str)

    if last_date == today and len(last_two) >= 2:
        second_last_kline = last_two[-2]
        if is_eastmoney:
            second_last_date_str = second_last_kline.split(",")[0]
        else:
            second_last_date_str = second_last_kline[0]
        return Utils.date.normalize_str(second_last_date_str)

    return last_date
