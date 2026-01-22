"""
股票列表 Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.data_class.field import DataSourceField
from core.modules.data_source.data_class.schema import DataSourceSchema


SCHEMA = DataSourceSchema(
    name="stock_list",
    description="股票列表",
    fields={
        "id": DataSourceField(str, required=True, description="股票代码ts_code"),
        "name": DataSourceField(str, required=True, description="股票名称"),
        "industry": DataSourceField(str, required=True, description="所属行业"),
        "type": DataSourceField(str, required=True, description="股票类型（市场）"),
        "exchange_center": DataSourceField(str, required=True, description="交易所"),
        "is_active": DataSourceField(int, required=True, description="是否活跃（1=活跃）"),
        "last_update": DataSourceField(str, required=True, description="最后更新时间（YYYY-MM-DD）"),
    }
)
