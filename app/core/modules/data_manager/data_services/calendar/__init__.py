"""
日历服务模块（CalendarService）

职责：
- 提供交易日相关的查询和缓存功能
"""
from .calendar_service import CalendarService

# 向后兼容：提供全局单例函数
_global_calendar_cache = None


def get_trading_date_cache():
    """
    获取全局交易日缓存实例（向后兼容函数）
    
    注意：此函数已废弃，请使用 DataManager.calendar 或 CalendarService 实例
    
    Returns:
        CalendarService 实例
    """
    global _global_calendar_cache
    if _global_calendar_cache is None:
        # 创建临时 DataManager 实例以获取 CalendarService
        from app.core.modules.data_manager import DataManager
        data_mgr = DataManager(is_verbose=False)
        _global_calendar_cache = data_mgr.calendar
    return _global_calendar_cache


# 向后兼容：TradingDateCache 作为 CalendarService 的别名
TradingDateCache = CalendarService

__all__ = ['CalendarService', 'TradingDateCache', 'get_trading_date_cache']
