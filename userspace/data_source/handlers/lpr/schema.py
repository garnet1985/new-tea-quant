"""
LPR利率数据（日度） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="lpr",
    description="LPR利率数据（日度）",
    schema={
        "date": Field(str, required=True, description="日期（YYYYMMDD）"),
        "lpr_1_y": Field(float, required=True, description="1年期LPR"),
        "lpr_5_y": Field(float, required=False, description="5年期LPR（可能为空）"),
    }
)
