"""
股指成分股权重数据（日度） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="stock_index_indicator_weight",
    description="股指成分股权重数据（日度）",
    schema={
        "id": Field(str, required=True, description="指数代码"),
        "date": Field(str, required=True, description="日期（YYYYMMDD）"),
        "stock_id": Field(str, required=True, description="成分股代码"),
        "weight": Field(float, required=True, description="权重"),
    }
)
