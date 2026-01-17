"""
复权因子事件数据（新表，只存储除权日） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="adj_factor_event",
    description="复权因子事件数据（新表，只存储除权日）",
    schema={
        "id": Field(str, required=True, description="股票代码ts_code"),
        "event_date": Field(str, required=True, description="除权除息日期（YYYYMMDD）"),
        "factor": Field(float, required=True, description="Tushare 复权因子 F(t)"),
        "qfq_diff": Field(float, required=False, description="与 EastMoney 前复权价格的固定差异（raw_price - eastmoney_qfq）"),
    }
)
