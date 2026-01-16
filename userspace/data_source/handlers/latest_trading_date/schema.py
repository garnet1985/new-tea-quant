"""
最新交易日 Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="latest_trading_date",
    description="最新交易日",
    schema={
        "date": Field(str, required=True, description="最新交易日（YYYYMMDD格式）"),
    }
)
