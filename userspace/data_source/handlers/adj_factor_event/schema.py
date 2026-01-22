"""
复权因子事件数据（新表，只存储除权日） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.data_class.field import DataSourceField
from core.modules.data_source.data_class.schema import DataSourceSchema


SCHEMA = DataSourceSchema(
    name="adj_factor_event",
    description="复权因子事件数据（新表，只存储除权日）",
    fields={
        "id": DataSourceField(str, required=True, description="股票代码ts_code"),
        "event_date": DataSourceField(str, required=True, description="除权除息日期（YYYYMMDD）"),
        "factor": DataSourceField(float, required=True, description="Tushare 复权因子 F(t)"),
        "qfq_diff": DataSourceField(float, required=False, description="与 EastMoney 前复权价格的固定差异（raw_price - eastmoney_qfq）"),
    }
)
