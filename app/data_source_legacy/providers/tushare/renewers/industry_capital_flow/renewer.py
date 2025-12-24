"""
行业资金流向更新器（同花顺）

使用 Tushare 的 moneyflow_ind_ths 接口获取行业资金流向数据
每日盘后更新，单次调用返回当日所有行业的数据
"""

from ...base_renewer import BaseRenewer


class IndustryCapitalFlowRenewer(BaseRenewer):
    """
    行业资金流向更新器
    
    特点：
    - 单API，简单宏观数据
    - 每个交易日返回约90个行业的数据
    - 直接继承BaseRenewer，无需特殊处理
    """
    pass

