"""
数据管理服务 - 统一的数据访问层

位置：app/data_manager/（应用层，与analyzer、data_source并列）

导出：
- DataManager: 数据管理器（主类）
- BaseTableNames: 基础表名枚举
- DataLoader: DataManager 的别名（向后兼容）

职责：
- 管理 DatabaseManager（唯一持有者）
- 初始化数据库、连接池、表结构
- 提供统一的数据访问 API
- 协调各专用 Loader

使用方式：
    from app.data_manager import DataManager
    
    # 初始化（自动创建数据库、连接池、表）
    data_mgr = DataManager(is_verbose=True)
    data_mgr.initialize()
    
    # 使用数据访问 API
    data = data_mgr.prepare_data(stock, settings)
    klines = data_mgr.load_klines('000001.SZ', term='daily', adjust='qfq')

架构说明：
- utils/db/ = 基础设施层（连接池、CRUD、Schema管理）
- app/data_manager/ = 数据访问层（业务数据服务、表管理）
- app/analyzer/ = 业务层（策略分析）
- app/data_source/ = 业务层（数据源管理）
"""

from .data_manager import DataManager
from .enums import BaseTableNames
from .data_services.trading_date.trading_date_cache import TradingDateCache, get_trading_date_cache

__all__ = ['DataManager', 'BaseTableNames', 'TradingDateCache', 'get_trading_date_cache']

# 向后兼容
DataLoader = DataManager

