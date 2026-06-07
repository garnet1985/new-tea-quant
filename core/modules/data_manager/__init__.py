"""
数据管理服务 - 统一的数据访问层（`modules.data_manager`）。

导出：
- `DataManager`：数据管理器（主入口）
- `BaseTableNames`：基础表名枚举
- `CalendarService`：日历与交易日服务

职责：
- 持有并初始化 `DatabaseManager`
- 发现并注册 `core/tables` 与 `userspace/extensions/tables` 下的 ORM 模型
- 通过 `data_services` 提供股票、宏观、日历、指数等访问 API

使用方式：
    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=True)  # 构造时即 initialize（幂等）
    klines = data_mgr.stock.kline.load("000001.SZ", term="daily", adjust="qfq")

文档：见模块内 `README.md` 与 `docs/`。
"""

from .data_manager import DataManager
from .enums import BaseTableNames
from .data_services.calendar import CalendarService

__all__ = ['DataManager', 'BaseTableNames', 'CalendarService']

