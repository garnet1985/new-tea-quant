"""
股指指标数据（指数K线，支持 daily/weekly/monthly 周期） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.data_class.field import DataSourceField
from core.modules.data_source.data_class.schema import DataSourceSchema


SCHEMA = DataSourceSchema(
    name="stock_index_indicator",
    description="股指指标数据（指数K线，支持 daily/weekly/monthly 周期）",
    fields={
        "id": DataSourceField(str, required=True, description="指数代码"),
        "term": DataSourceField(str, required=True, description="K线周期（daily/weekly/monthly）"),
        "date": DataSourceField(str, required=True, description="交易日期（YYYYMMDD）"),
        "open": DataSourceField(float, required=True, description="开盘价"),
        "close": DataSourceField(float, required=True, description="收盘价"),
        "highest": DataSourceField(float, required=True, description="最高价"),
        "lowest": DataSourceField(float, required=True, description="最低价"),
        "pre_close": DataSourceField(float, required=True, description="昨收价"),
        "price_change_delta": DataSourceField(float, required=True, description="涨跌额"),
        "price_change_rate_delta": DataSourceField(float, required=True, description="涨跌幅"),
        "volume": DataSourceField(int, required=True, description="成交量"),
        "amount": DataSourceField(float, required=True, description="成交额"),
    }
)
