"""
GDP数据（季度） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="gdp",
    description="GDP数据（季度）",
    schema={
        "quarter": Field(str, required=True, description="季度（YYYYQ[1-4]）"),
        "gdp": Field(float, required=True, description="GDP"),
        "gdp_yoy": Field(float, required=True, description="GDP同比"),
        "primary_industry": Field(float, required=True, description="第一产业"),
        "primary_industry_yoy": Field(float, required=True, description="第一产业同比"),
        "secondary_industry": Field(float, required=True, description="第二产业"),
        "secondary_industry_yoy": Field(float, required=True, description="第二产业同比"),
        "tertiary_industry": Field(float, required=True, description="第三产业"),
        "tertiary_industry_yoy": Field(float, required=True, description="第三产业同比"),
    }
)
