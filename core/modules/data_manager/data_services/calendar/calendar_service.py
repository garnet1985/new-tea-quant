"""
日历服务（CalendarService）

职责：
- 封装交易日相关的查询和缓存
- 提供日期相关的业务方法

特性：
- 内存缓存：快速访问，进程内共享
- 智能刷新：每天只请求一次 API
- 数据库缓存：使用 system_cache 持久化缓存，降低API调用频率
- 多Fallback机制：东方财富 → 新浪财经 → 系统猜测
- 线程安全：支持多线程访问
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from loguru import logger
import threading
import json

from core.utils.date.date_utils import DateUtils
from core.modules.data_source.service.provider_helper import DataSourceProviderHelper
from .. import BaseDataService


class CalendarService(BaseDataService):
    """
    日历服务
    
    使用方式：
        calendar = CalendarService(data_manager)
        latest_date = calendar.get_latest_trading_date()
    """
    
    # 类级别的内存缓存（进程内共享）
    _memory_cache = {
        "last_trading_date": None,      # 上次交易日（YYYYMMDD）
        "last_request_date": None,       # 上次请求日期（YYYYMMDD）
        "lock": threading.Lock()         # 线程锁
    }
    
    def __init__(self, data_manager):
        """
        初始化日历服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
    
    def get_latest_completed_trading_date(self) -> str:
        # TODO: need to be refactored, now data is handled by data_source
        """
        获取最新已完成交易日（不是今天，即使今天已经收盘）
        
        逻辑：
        1. 检查内存缓存（进程内缓存）
        2. 如果今天已经请求过，直接返回缓存
        3. 检查数据库缓存（system_cache）
        4. 如果数据库缓存是今天更新的，直接返回并更新内存缓存
        5. 如果缓存过期，从多个API fallback获取
        6. 更新内存缓存和数据库缓存
        
        Returns:
            最新已完成交易日（YYYYMMDD，不是今天）
        """
        today = DateUtils.get_current_date_str()
        
        # 1. 检查内存缓存（如果今天已请求过，直接返回）
        cached_date = self._get_cache_from_memory()
        if cached_date:
            return cached_date
        
        # 2. 检查数据库缓存
        db_cache_result = self._get_cache_from_db()
        if db_cache_result:
            cached_date, updated_at = db_cache_result
            
            # 如果缓存未过期（今天更新的），使用它
            if not self._is_cache_expired(updated_at):
                self._save_to_memory_cache(cached_date)
                return cached_date
        
        # 3. 缓存过期或不存在，从API获取（多fallback机制）
        new_trading_date, provider = self._fetch_with_fallback()
        
        # 4. 记录交易日变化（如果有）
        old_cached_date = self._get_cache_from_memory()
        if old_cached_date and new_trading_date != old_cached_date:
            logger.info(f"📅 交易日更新: {old_cached_date} -> {new_trading_date} (来源: {provider})")
        
        # 5. 更新缓存（内存 + 数据库）
        self._save_to_memory_cache(new_trading_date)
        self._save_to_db_cache(new_trading_date, today, provider)
        
        return new_trading_date

    def _get_cache_from_memory(self) -> Optional[str]:
        """
        从内存缓存中获取最新交易日（仅当今天已请求过时返回）
        
        Returns:
            缓存的交易日，如果今天未请求过或不存在返回 None
        """
        today = DateUtils.get_current_date_str()
        with self._memory_cache["lock"]:
            last_request_date = self._memory_cache["last_request_date"]
            last_trading_date = self._memory_cache["last_trading_date"]
            
            # 只有今天已请求过才返回缓存
            if last_request_date == today and last_trading_date:
                return last_trading_date
            return None

    def _get_cache_from_db(self) -> Optional[Tuple[str, str]]:
        """
        从数据库缓存中获取最新交易日（包含过期检查）
        
        Returns:
            Tuple[交易日（YYYYMMDD）, 更新时间（YYYYMMDD）]，如果缓存不存在或过期返回 None
        """
        try:
            cache_model = self.data_manager.get_table("sys_cache")
            cache_data = cache_model.load_by_key("latest_completed_trading_date")

            if not cache_data:
                return None

            # 优先从 json 字段读取，其次退回 text
            raw_value = cache_data.get("json") or cache_data.get("text")
            if not raw_value:
                return None

            # 解析缓存值（JSON 格式）
            try:
                if isinstance(raw_value, str):
                    cache_info = json.loads(raw_value)
                else:
                    cache_info = raw_value

                cached_date = cache_info.get("date")
                updated_at = cache_info.get("updated_at")

                if not cached_date or not updated_at:
                    return None

                # 返回日期和更新时间
                return (cached_date, updated_at)

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"解析数据库缓存失败: {e}")
                return None

        except Exception as e:
            logger.warning(f"读取数据库缓存失败: {e}")
            return None

    def _save_to_memory_cache(self, date: str):
        """
        保存最新交易日到内存缓存
        
        Args:
            date: 最新交易日（YYYYMMDD）
        """
        with self._memory_cache["lock"]:
            self._memory_cache["last_trading_date"] = date
            self._memory_cache["last_request_date"] = DateUtils.get_current_date_str()

    def _save_to_db_cache(self, date: str, updated_at: str, provider: str):
        """
        保存最新交易日到数据库缓存
        
        Args:
            date: 最新交易日（YYYYMMDD）
            updated_at: 更新时间（YYYYMMDD）
            provider: 数据来源（如 'eastmoney', 'sina', 'guess'）
        """
        try:
            cache_model = self.data_manager.get_table("sys_cache")
            cache_model.save_by_key(
                "latest_completed_trading_date",
                json={
                    "date": date,
                    "updated_at": updated_at,
                    "provider": provider,
                },
            )
        except Exception as e:
            logger.warning(f"保存数据库缓存失败: {e}")

    def _is_cache_expired(self, updated_at: str) -> bool:
        """
        判断缓存是否过期
        
        Args:
            updated_at: 更新时间（YYYYMMDD）
            
        Returns:
            True 表示缓存已过期（不是今天更新的），False 表示缓存有效
        """
        return updated_at != DateUtils.get_current_date_str()

    def refresh(self) -> str:
        """
        强制刷新最新交易日（忽略所有缓存）
        
        Returns:
            最新交易日（YYYYMMDD）
        """
        today = DateUtils.get_current_date_str()
        
        logger.info("🔄 强制刷新最新交易日（忽略缓存）...")
        new_trading_date, provider = self._fetch_with_fallback()
        
        # 更新缓存
        self._save_to_memory_cache(new_trading_date)
        self._save_to_db_cache(new_trading_date, today, provider)
        
        return new_trading_date
    
    def get_cached_date(self) -> Optional[str]:
        """
        获取缓存的交易日（不触发 API 请求）
        
        优先从内存缓存获取，如果不存在则从数据库缓存获取（不检查过期）
        
        Returns:
            缓存的交易日，不存在返回 None
        """
        # 先尝试内存缓存
        cached_date = self._get_cache_from_memory()
        if cached_date:
            return cached_date
        
        # 再尝试数据库缓存（不检查过期）
        db_cache_result = self._get_cache_from_db()
        if db_cache_result:
            cached_date, _ = db_cache_result
            return cached_date
        
        return None
    
    def _fetch_with_fallback(self) -> Tuple[str, str]:
        """
        使用多fallback机制获取最新交易日
        
        Fallback 优先级：
        1. 东方财富API - 查询上证指数K线，取最后2根判断
        2. 新浪财经API - 查询上证指数K线，取最后2根判断
        3. 系统猜测 - 从昨天开始排除周末
        
        Returns:
            Tuple[最新交易日（YYYYMMDD）, 数据来源（provider名称）]
        """
        # Fallback 1: 东方财富API
        latest_date = self._try_fetch_from_provider('东方财富', self._fetch_from_eastmoney)
        if latest_date:
            return latest_date, 'eastmoney'
        
        # Fallback 2: 新浪财经API
        latest_date = self._try_fetch_from_provider('新浪财经', self._fetch_from_sina)
        if latest_date:
            return latest_date, 'sina'
        
        # Fallback 3: 系统猜测（排除周末）
        logger.warning("⚠️  所有API都失败，使用系统猜测（排除周末）")
        latest_date = self._guess_latest_trading_date()
        return latest_date, 'guess'
    
    def _try_fetch_from_provider(self, provider_name: str, fetch_func) -> Optional[str]:
        """
        尝试从指定provider获取最新交易日
        
        Args:
            provider_name: Provider名称（用于日志）
            fetch_func: 获取函数
        
        Returns:
            最新交易日（YYYYMMDD），如果失败或日期是今天返回 None
        """
        today = DateUtils.get_current_date_str()
        try:
            latest_date = fetch_func()
            if latest_date and latest_date != today:
                logger.info(f"✅ 从{provider_name}API获取最新交易日: {latest_date}")
                return latest_date
        except Exception as e:
            logger.warning(f"⚠️  {provider_name}API失败: {e}")
        return None
    
    def _fetch_from_eastmoney(self) -> Optional[str]:
        """
        从东方财富API获取最新交易日
        
        查询上证指数（000001.SH）的K线数据，取最后2根K线
        
        Returns:
            最新已完成交易日（YYYYMMDD），如果失败返回 None
        """
        try:
            provider = DataSourceProviderHelper.get_provider("eastmoney")
            if not provider:
                raise ValueError("EastMoney Provider 未找到")
            
            # 上证指数在东方财富的代码格式：1.000001（沪市指数）
            result = provider.get_qfq_kline(secid="1.000001", limit=2)
            
            if not result or 'data' not in result:
                raise ValueError("东方财富API返回数据格式错误")
            
            klines = result.get('data', {}).get('klines', [])
            if not klines or len(klines) < 1:
                raise ValueError("未获取到K线数据")
            
            # 解析K线数据（格式：字符串数组，每个元素为 "日期,收盘价,..."）
            return self._extract_latest_date_from_klines(klines, is_eastmoney=True)
            
        except Exception as e:
            logger.error(f"❌ 从东方财富API获取最新交易日失败: {e}")
            raise
    
    def _fetch_from_sina(self) -> Optional[str]:
        """
        从新浪财经API获取最新交易日
        
        查询上证指数（sh000001）的K线数据，取最后2根K线
        
        Returns:
            最新已完成交易日（YYYYMMDD），如果失败返回 None
        """
        try:
            provider = DataSourceProviderHelper.get_provider("sina")
            if not provider:
                raise ValueError("Sina Provider 未找到")
            
            # 上证指数在新浪财经的代码格式：sh000001
            result = provider.get_daily_kline(symbol="sh000001", datalen=2)
            
            if not result or 'data' not in result:
                raise ValueError("新浪财经API返回数据格式错误")
            
            klines = result.get('data', [])
            if not klines or len(klines) < 1:
                raise ValueError("未获取到K线数据")
            
            # 解析K线数据（格式：数组，每个元素为 ["日期", "开盘", "最高", "最低", "收盘", "成交量"]）
            return self._extract_latest_date_from_klines(klines, is_eastmoney=False)
            
        except Exception as e:
            logger.error(f"❌ 从新浪财经API获取最新交易日失败: {e}")
            raise
    
    def _extract_latest_date_from_klines(self, klines: list, is_eastmoney: bool) -> str:
        """
        从K线数据中提取最新已完成交易日
        
        逻辑：
        - 取最后2根K线
        - 如果最后一根的日期 == 今天，使用倒数第二根的日期
        - 否则使用最后一根的日期
        
        Args:
            klines: K线数据列表
                - 东方财富格式：字符串数组，每个元素为 "日期,收盘价,..."
                - 新浪财经格式：数组，每个元素为 ["日期", "开盘", "最高", "最低", "收盘", "成交量"]
            is_eastmoney: 是否为东方财富格式
        
        Returns:
            最新已完成交易日（YYYYMMDD）
        """
        # 取最后2根
        last_two = klines[-2:] if len(klines) >= 2 else [klines[-1]]
        today = DateUtils.get_current_date_str()
        
        # 解析最后一根K线的日期
        last_kline = last_two[-1]
        if is_eastmoney:
            # 东方财富格式：字符串 "日期,收盘价,..."
            last_date_str = last_kline.split(',')[0]
        else:
            # 新浪财经格式：数组 ["日期", ...]
            last_date_str = last_kline[0]
        
        last_date = DateUtils.yyyy_mm_dd_to_yyyymmdd(last_date_str)
        
        # 如果最后一根是今天，使用倒数第二根
        if last_date == today and len(last_two) >= 2:
            second_last_kline = last_two[-2]
            if is_eastmoney:
                second_last_date_str = second_last_kline.split(',')[0]
            else:
                second_last_date_str = second_last_kline[0]
            return DateUtils.yyyy_mm_dd_to_yyyymmdd(second_last_date_str)
        
        # 否则使用最后一根
        return last_date
    
    def _guess_latest_trading_date(self) -> str:
        """
        系统猜测最新交易日（最后兜底方案）
        
        从昨天开始往前找，排除周末（周六、周日）
        注意：此方法无法排除节假日，只能排除周末
        
        Returns:
            猜测的最新交易日（YYYYMMDD）
        """
        today = datetime.now()
        current = today - timedelta(days=1)  # 从昨天开始
        
        # 最多往前找7天（避免无限循环）
        max_days = 7
        for _ in range(max_days):
            # 排除周末（周六=5, 周日=6）
            weekday = current.weekday()
            if weekday < 5:  # 周一到周五（0-4）
                date_str = current.strftime('%Y%m%d')
                logger.warning(f"⚠️  使用系统猜测的最新交易日: {date_str}（可能不准确，未排除节假日）")
                return date_str
            
            # 往前推一天
            current -= timedelta(days=1)
        
        # 如果7天内都没找到，返回昨天（虽然可能是周末）
        yesterday = (today - timedelta(days=1)).strftime('%Y%m%d')
        logger.warning(f"⚠️  系统猜测失败，使用昨天: {yesterday}")
        return yesterday
