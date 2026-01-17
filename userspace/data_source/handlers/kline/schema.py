"""
K线数据（支持 daily/weekly/monthly 周期） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="kline",
    description="K线数据（支持 daily/weekly/monthly 周期）",
    schema={
        "id": Field(str, required=True, description="股票代码ts_code"),
        "term": Field(str, required=True, description="K线周期（daily/weekly/monthly）"),
        "date": Field(str, required=True, description="交易日期（YYYYMMDD）"),
        "open": Field(float, required=True, description="开盘价"),
        "close": Field(float, required=True, description="收盘价"),
        "highest": Field(float, required=True, description="最高价"),
        "lowest": Field(float, required=True, description="最低价"),
        "pre_close": Field(float, required=True, description="昨收价（除权价，前复权）"),
        "price_change_delta": Field(float, required=True, description="涨跌额"),
        "price_change_rate_delta": Field(float, required=True, description="涨跌幅"),
        "volume": Field(int, required=True, description="成交量"),
        "amount": Field(float, required=True, description="成交额"),
        "turnover_rate": Field(float, required=False, description="换手率"),
        "free_turnover_rate": Field(float, required=False, description="自由流通股换手率"),
        "volume_ratio": Field(float, required=False, description="量比"),
        "pe": Field(float, required=False, description="市盈率"),
        "pe_ttm": Field(float, required=False, description="市盈率TTM"),
        "pb": Field(float, required=False, description="市净率"),
        "ps": Field(float, required=False, description="市销率"),
        "ps_ttm": Field(float, required=False, description="市销率TTM"),
        "dv_ratio": Field(float, required=False, description="分红比例"),
        "dv_ttm": Field(float, required=False, description="分红比例TTM"),
        "total_share": Field(int, required=False, description="总股本"),
        "float_share": Field(int, required=False, description="流通股本"),
        "free_share": Field(int, required=False, description="自由流通股本"),
        "total_market_value": Field(float, required=False, description="总市值"),
        "circ_market_value": Field(float, required=False, description="流通市值"),
    }
)
