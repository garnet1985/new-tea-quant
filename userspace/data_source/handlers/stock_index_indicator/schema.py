"""
股指指标数据（指数K线，支持 daily/weekly/monthly 周期） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="stock_index_indicator",
    description="股指指标数据（指数K线，支持 daily/weekly/monthly 周期）",
    schema={
        "id": Field(str, required=True, description="指数代码"),
        "term": Field(str, required=True, description="K线周期（daily/weekly/monthly）"),
        "date": Field(str, required=True, description="交易日期（YYYYMMDD）"),
        "open": Field(float, required=True, description="开盘价"),
        "close": Field(float, required=True, description="收盘价"),
        "highest": Field(float, required=True, description="最高价"),
        "lowest": Field(float, required=True, description="最低价"),
        "pre_close": Field(float, required=True, description="昨收价"),
        "price_change_delta": Field(float, required=True, description="涨跌额"),
        "price_change_rate_delta": Field(float, required=True, description="涨跌幅"),
        "volume": Field(int, required=True, description="成交量"),
        "amount": Field(float, required=True, description="成交额"),
    }
)
