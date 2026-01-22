"""
K线数据（支持 daily/weekly/monthly 周期） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.data_class.field import DataSourceField
from core.modules.data_source.data_class.schema import DataSourceSchema


SCHEMA = DataSourceSchema(
    name="kline",
    description="K线数据（支持 daily/weekly/monthly 周期）",
    fields={
        "id": DataSourceField(str, required=True, description="股票代码ts_code"),
        "term": DataSourceField(str, required=True, description="K线周期（daily/weekly/monthly）"),
        "date": DataSourceField(str, required=True, description="交易日期（YYYYMMDD）"),
        "open": DataSourceField(float, required=True, description="开盘价"),
        "close": DataSourceField(float, required=True, description="收盘价"),
        "highest": DataSourceField(float, required=True, description="最高价"),
        "lowest": DataSourceField(float, required=True, description="最低价"),
        "pre_close": DataSourceField(float, required=True, description="昨收价（除权价，前复权）"),
        "price_change_delta": DataSourceField(float, required=True, description="涨跌额"),
        "price_change_rate_delta": DataSourceField(float, required=True, description="涨跌幅"),
        "volume": DataSourceField(int, required=True, description="成交量"),
        "amount": DataSourceField(float, required=True, description="成交额"),
        "turnover_rate": DataSourceField(float, required=False, description="换手率"),
        "free_turnover_rate": DataSourceField(float, required=False, description="自由流通股换手率"),
        "volume_ratio": DataSourceField(float, required=False, description="量比"),
        "pe": DataSourceField(float, required=False, description="市盈率"),
        "pe_ttm": DataSourceField(float, required=False, description="市盈率TTM"),
        "pb": DataSourceField(float, required=False, description="市净率"),
        "ps": DataSourceField(float, required=False, description="市销率"),
        "ps_ttm": DataSourceField(float, required=False, description="市销率TTM"),
        "dv_ratio": DataSourceField(float, required=False, description="分红比例"),
        "dv_ttm": DataSourceField(float, required=False, description="分红比例TTM"),
        "total_share": DataSourceField(int, required=False, description="总股本"),
        "float_share": DataSourceField(int, required=False, description="流通股本"),
        "free_share": DataSourceField(int, required=False, description="自由流通股本"),
        "total_market_value": DataSourceField(float, required=False, description="总市值"),
        "circ_market_value": DataSourceField(float, required=False, description="流通市值"),
    }
)
