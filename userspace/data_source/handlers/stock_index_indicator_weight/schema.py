"""
股指成分股权重数据（日度） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.data_class.field import DataSourceField
from core.modules.data_source.data_class.schema import DataSourceSchema


SCHEMA = DataSourceSchema(
    name="stock_index_indicator_weight",
    description="股指成分股权重数据（日度）",
    fields={
        "id": DataSourceField(str, required=True, description="指数代码"),
        "date": DataSourceField(str, required=True, description="日期（YYYYMMDD）"),
        "stock_id": DataSourceField(str, required=True, description="成分股代码"),
        "weight": DataSourceField(float, required=True, description="权重"),
    }
)
