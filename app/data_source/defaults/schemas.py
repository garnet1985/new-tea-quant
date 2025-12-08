from dataclasses import dataclass
from typing import Any, Optional, Callable


@dataclass
class Field:
    type: type
    required: bool = True
    default: Optional[Any] = None
    description: str = ""
    validator: Optional[Callable] = None


class DataSourceSchema:
    
    def __init__(self, name: str, schema: dict, description: str = ""):
        self.name = name
        self.schema = schema
        self.description = description
    
    def validate(self, data: dict) -> bool:
        pass


STOCK_LIST = DataSourceSchema(
    name="stock_list",
    description="股票列表",
    schema={}
)

DAILY_KLINE = DataSourceSchema(
    name="daily_kline",
    description="日线数据",
    schema={}
)

WEEKLY_KLINE = DataSourceSchema(
    name="weekly_kline",
    description="周线数据",
    schema={}
)

MONTHLY_KLINE = DataSourceSchema(
    name="monthly_kline",
    description="月线数据",
    schema={}
)

CORPORATE_FINANCE = DataSourceSchema(
    name="corporate_finance",
    description="财务数据",
    schema={}
)

GDP = DataSourceSchema(
    name="gdp",
    description="GDP数据",
    schema={}
)

CPI = DataSourceSchema(
    name="cpi",
    description="CPI数据",
    schema={}
)

PPI = DataSourceSchema(
    name="ppi",
    description="PPI数据",
    schema={}
)

PMI = DataSourceSchema(
    name="pmi",
    description="PMI数据",
    schema={}
)

SHIBOR = DataSourceSchema(
    name="shibor",
    description="Shibor数据",
    schema={}
)

LPR = DataSourceSchema(
    name="lpr",
    description="LPR数据",
    schema={}
)

MONEY_SUPPLY = DataSourceSchema(
    name="money_supply",
    description="货币供应量数据",
    schema={}
)

ADJ_FACTOR = DataSourceSchema(
    name="adj_factor",
    description="复权因子",
    schema={}
)


DEFAULT_SCHEMAS = {
    "stock_list": STOCK_LIST,
    "daily_kline": DAILY_KLINE,
    "weekly_kline": WEEKLY_KLINE,
    "monthly_kline": MONTHLY_KLINE,
    "corporate_finance": CORPORATE_FINANCE,
    "gdp": GDP,
    "cpi": CPI,
    "ppi": PPI,
    "pmi": PMI,
    "shibor": SHIBOR,
    "lpr": LPR,
    "money_supply": MONEY_SUPPLY,
    "adj_factor": ADJ_FACTOR,
}

