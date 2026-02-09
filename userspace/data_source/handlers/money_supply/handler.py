"""
Money Supply Handler - 货币供应量

从 Tushare 获取货币供应量数据，写入 sys_money_supply 表。

注意：
- 日期标准化由 BaseHandler 根据 config 中的 date_format 自动处理
- 缺失字段会存为 NULL（符合 schema 的 nullable: true 设计）
"""
from core.modules.data_source.base_class.base_handler import BaseHandler


class MoneySupplyHandler(BaseHandler):
    """货币供应量 Handler，绑定表 sys_money_supply。"""
    # BaseHandler 会自动处理日期标准化和数据规范化
    # 缺失字段会按 schema 的 nullable 设置存为 NULL
    pass
