"""
Shibor利率数据（日度） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.data_class.field import DataSourceField
from core.modules.data_source.data_class.schema import DataSourceSchema


SCHEMA = DataSourceSchema(
    name="shibor",
    description="Shibor利率数据（日度）",
    fields={
        "date": DataSourceField(str, required=True, description="日期（YYYYMMDD）"),
        "one_night": DataSourceField(float, required=True, description="隔夜"),
        "one_week": DataSourceField(float, required=True, description="1周"),
        "one_month": DataSourceField(float, required=True, description="1个月"),
        "three_month": DataSourceField(float, required=True, description="3个月"),
        "one_year": DataSourceField(float, required=True, description="1年"),
    }
)
