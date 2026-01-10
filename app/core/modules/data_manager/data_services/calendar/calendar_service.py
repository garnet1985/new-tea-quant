"""
日历服务（CalendarService）

职责：
- 封装交易日相关的查询和缓存
- 提供日期相关的业务方法

特性：
- 内存缓存：快速访问，进程内共享
- 智能刷新：每天只请求一次 API
- 线程安全：支持多线程访问
"""
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
import threading

from app.core.utils.date.date_utils import DateUtils
from app.core.modules.data_source.providers.provider_instance_pool import get_provider_pool
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
    
    def get_latest_trading_date(self) -> str:
        """
        获取最新交易日
        
        逻辑：
        1. 检查内存缓存
        2. 如果今天已经请求过，直接返回缓存
        3. 如果今天还没请求过，从 API 获取
        4. 更新内存缓存
        
        Returns:
            最新交易日（YYYYMMDD）
        """
        today = DateUtils.get_current_date_str()  # "20241001"
        
        # 线程安全：获取锁
        with self._memory_cache["lock"]:
            # 1. 检查内存缓存
            last_request_date = self._memory_cache["last_request_date"]
            last_trading_date = self._memory_cache["last_trading_date"]
            
            # 2. 如果今天已经请求过，直接返回缓存
            if last_request_date == today and last_trading_date:
                logger.debug(f"使用内存缓存的最新交易日: {last_trading_date}")
                return last_trading_date
            
            # 3. 需要从 API 获取
            logger.info("🔄 刷新最新交易日...")
            new_trading_date = self._fetch_from_api()
            
            # 4. 更新缓存
            # 如果交易日有变化，记录日志
            if last_trading_date and new_trading_date != last_trading_date:
                logger.info(f"📅 交易日更新: {last_trading_date} -> {new_trading_date}")
            
            # 更新内存缓存
            self._memory_cache["last_trading_date"] = new_trading_date
            self._memory_cache["last_request_date"] = today
            
            return new_trading_date
    
    def get_latest_completed_trading_date(self) -> str:
        """
        获取最新已完成交易日（与 get_latest_trading_date 功能相同）
        
        为了向后兼容，保留此方法
        
        Returns:
            最新交易日（YYYYMMDD）
        """
        return self.get_latest_trading_date()
    
    def refresh(self) -> str:
        """
        强制刷新最新交易日（忽略缓存）
        
        Returns:
            最新交易日（YYYYMMDD）
        """
        today = DateUtils.get_current_date_str()
        
        with self._memory_cache["lock"]:
            logger.info("🔄 强制刷新最新交易日...")
            new_trading_date = self._fetch_from_api()
            
            # 更新缓存
            self._memory_cache["last_trading_date"] = new_trading_date
            self._memory_cache["last_request_date"] = today
            
            return new_trading_date
    
    def get_cached_date(self) -> Optional[str]:
        """
        获取缓存的交易日（不触发 API 请求）
        
        Returns:
            缓存的交易日，不存在返回 None
        """
        with self._memory_cache["lock"]:
            return self._memory_cache["last_trading_date"]
    
    def _fetch_from_api(self) -> str:
        """
        从 API 获取最新交易日
        
        Returns:
            最新交易日（YYYYMMDD）
        """
        try:
            # 获取 Tushare Provider
            pool = get_provider_pool()
            provider = pool.get_provider("tushare")
            if not provider:
                raise ValueError("Tushare Provider 未找到")
            
            # 计算查询日期范围（从昨天往前推 15 天）
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            end_date = yesterday.strftime('%Y%m%d')
            start_date = (yesterday - timedelta(days=15)).strftime('%Y%m%d')
            
            # 调用 API
            df = provider.get_trade_cal(
                exchange="",  # 空字符串表示所有交易所
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                raise ValueError("交易日历查询返回空数据")
            
            # 检查字段名
            if 'is_open' not in df.columns:
                raise ValueError("交易日历数据缺少 is_open 字段")
            
            # 筛选交易日（is_open == 1）
            trading_days = df[df['is_open'] == 1]
            
            if trading_days.empty:
                raise ValueError("未找到交易日")
            
            # 获取最大日期（最新交易日）
            latest_date = str(trading_days['cal_date'].max())
            
            logger.info(f"✅ 从 API 获取最新交易日: {latest_date}")
            return latest_date
            
        except Exception as e:
            logger.error(f"❌ 从 API 获取最新交易日失败: {e}")
            # 如果 API 失败，尝试使用昨天作为默认值
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            logger.warning(f"使用昨天作为默认值: {yesterday}")
            return yesterday
