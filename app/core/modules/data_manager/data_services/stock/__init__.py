"""
股票数据服务模块（StockService）

目录结构：
- stock_service.py      - 主服务类（统一入口）
- sub_services/         - 子服务目录
    - kline_service.py      - K线数据服务
    - tag_service.py        - 标签数据服务
    - corporate_finance_service.py  - 财务数据服务
    - list_service.py       - 股票列表服务
- helpers/              - 辅助工具
    - adjustment.py      - 复权计算工具
"""

from .stock_service import StockService
from .sub_services import ListService, KlineService, TagDataService, CorporateFinanceService

__all__ = [
    'StockService',
    'ListService',
    'KlineService',
    'TagDataService',
    'CorporateFinanceService',
]
