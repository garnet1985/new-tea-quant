from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_contract.loaders.stock_kline import StockKlineLoader
from core.modules.data_contract.loaders.stock_kline_qfq import StockKlineQfqLoader
from core.modules.data_contract.loaders.stock_list import StockListLoader

LOADER_REGISTRY = {
    "stock.list": StockListLoader,
    "stock.kline.daily.nfq": StockKlineLoader,
    "stock.kline.daily.qfq": StockKlineQfqLoader,
}

__all__ = [
    "BaseLoader",
    "LOADER_REGISTRY",
    "StockListLoader",
    "StockKlineLoader",
    "StockKlineQfqLoader",
]
