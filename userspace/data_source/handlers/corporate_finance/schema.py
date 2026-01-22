"""
企业财务数据（季度） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.data_class.field import DataSourceField
from core.modules.data_source.data_class.schema import DataSourceSchema


SCHEMA = DataSourceSchema(
    name="corporate_finance",
    description="企业财务数据（季度）",
    fields={
        "id": DataSourceField(str, required=True, description="股票代码ts_code"),
        "quarter": DataSourceField(str, required=True, description="季度（YYYYQ[1-4]）"),
        "eps": DataSourceField(float, required=True, description="每股收益"),
        "dt_eps": DataSourceField(float, required=True, description="稀释每股收益"),
        "roe": DataSourceField(float, required=True, description="净资产收益率"),
        "roe_dt": DataSourceField(float, required=True, description="扣非净资产收益率"),
        "roa": DataSourceField(float, required=True, description="总资产收益率"),
        "netprofit_margin": DataSourceField(float, required=True, description="销售净利率"),
        "gross_profit_margin": DataSourceField(float, required=True, description="毛利率"),
        "op_income": DataSourceField(float, required=True, description="经营活动净收益"),
        "roic": DataSourceField(float, required=True, description="投入资本回报率"),
        "ebit": DataSourceField(float, required=True, description="息税前利润"),
        "ebitda": DataSourceField(float, required=True, description="息税折旧摊销前利润"),
        "dtprofit_to_profit": DataSourceField(float, required=True, description="扣非净利润/净利润"),
        "profit_dedt": DataSourceField(float, required=True, description="净利润/扣非净利润"),
        "or_yoy": DataSourceField(float, required=True, description="营业收入同比增长率(%)"),
        "netprofit_yoy": DataSourceField(float, required=True, description="净利润同比增长率(%)"),
        "basic_eps_yoy": DataSourceField(float, required=True, description="每股收益同比增长率(%)"),
        "dt_eps_yoy": DataSourceField(float, required=True, description="稀释每股收益同比增长率(%)"),
        "tr_yoy": DataSourceField(float, required=True, description="营业总收入同比增长率(%)"),
        "netdebt": DataSourceField(float, required=True, description="净债务"),
        "debt_to_eqt": DataSourceField(float, required=True, description="产权比率"),
        "debt_to_assets": DataSourceField(float, required=True, description="资产负债率"),
        "interestdebt": DataSourceField(float, required=True, description="带息债务"),
        "assets_to_eqt": DataSourceField(float, required=True, description="权益乘数"),
        "quick_ratio": DataSourceField(float, required=True, description="速动比率"),
        "current_ratio": DataSourceField(float, required=True, description="流动比率"),
        "ar_turn": DataSourceField(float, required=True, description="应收账款周转率"),
        "bps": DataSourceField(float, required=True, description="每股净资产"),
        "ocfps": DataSourceField(float, required=True, description="每股经营活动产生的现金流量净额"),
        "fcff": DataSourceField(float, required=True, description="企业自由现金流量"),
        "fcfe": DataSourceField(float, required=True, description="股东自由现金流量"),
    }
)
