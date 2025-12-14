"""
Data Loaders

⚠️ 状态：正在使用中，但建议逐步迁移到 DataService 架构

专用数据加载器：
- KlineLoader: K线数据加载
- LabelLoader: 标签数据加载
- MacroEconomyLoader: 宏观经济数据加载
- CorporateFinanceLoader: 企业财务数据加载

注意：
- 这些 Loaders 目前仍在 DataManager 中被大量使用
- 新代码建议优先使用 DataService（位于 data_services/）
- 旧代码保持使用 Loaders（向后兼容）
- 详见 loaders/README.md
"""

from .kline_loader import KlineLoader
from .label_loader import LabelLoader
from .macro_loader import MacroEconomyLoader
from .corporate_finance_loader import CorporateFinanceLoader

__all__ = [
    'KlineLoader',
    'LabelLoader',
    'MacroEconomyLoader',
    'CorporateFinanceLoader',
]
