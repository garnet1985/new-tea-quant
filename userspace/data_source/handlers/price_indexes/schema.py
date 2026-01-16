"""
价格指数数据（月度，包含CPI/PPI/PMI/货币供应量） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="price_indexes",
    description="价格指数数据（月度，包含CPI/PPI/PMI/货币供应量）",
    schema={
        "date": Field(str, required=True, description="月份（YYYYMM）"),
        "cpi": Field(float, required=True, description="CPI当月值"),
        "cpi_yoy": Field(float, required=True, description="CPI同比"),
        "cpi_mom": Field(float, required=True, description="CPI环比"),
        "ppi": Field(float, required=True, description="PPI当月值"),
        "ppi_yoy": Field(float, required=True, description="PPI同比"),
        "ppi_mom": Field(float, required=True, description="PPI环比"),
        "pmi": Field(float, required=True, description="PMI综合指数"),
        "pmi_l_scale": Field(float, required=True, description="大型企业PMI"),
        "pmi_m_scale": Field(float, required=True, description="中型企业PMI"),
        "pmi_s_scale": Field(float, required=True, description="小型企业PMI"),
        "m0": Field(float, required=True, description="M0货币供应量"),
        "m0_yoy": Field(float, required=True, description="M0同比"),
        "m0_mom": Field(float, required=True, description="M0环比"),
        "m1": Field(float, required=True, description="M1货币供应量"),
        "m1_yoy": Field(float, required=True, description="M1同比"),
        "m1_mom": Field(float, required=True, description="M1环比"),
        "m2": Field(float, required=True, description="M2货币供应量"),
        "m2_yoy": Field(float, required=True, description="M2同比"),
        "m2_mom": Field(float, required=True, description="M2环比"),
    }
)
