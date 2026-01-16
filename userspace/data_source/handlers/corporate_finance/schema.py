"""
企业财务数据（季度） Schema 定义

定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
schema 中的 key 是数据库字段名（normalize 后的输出字段名）
"""
from core.modules.data_source.schemas import Field, DataSourceSchema


SCHEMA = DataSourceSchema(
    name="corporate_finance",
    description="企业财务数据（季度）",
    schema={
        "id": Field(str, required=True, description="股票代码ts_code"),
        "quarter": Field(str, required=True, description="季度（YYYYQ[1-4]）"),
        "eps": Field(float, required=True, description="每股收益"),
        "dt_eps": Field(float, required=True, description="稀释每股收益"),
        "roe": Field(float, required=True, description="净资产收益率"),
        "roe_dt": Field(float, required=True, description="扣非净资产收益率"),
        "roa": Field(float, required=True, description="总资产收益率"),
        "netprofit_margin": Field(float, required=True, description="销售净利率"),
        "gross_profit_margin": Field(float, required=True, description="毛利率"),
        "op_income": Field(float, required=True, description="经营活动净收益"),
        "roic": Field(float, required=True, description="投入资本回报率"),
        "ebit": Field(float, required=True, description="息税前利润"),
        "ebitda": Field(float, required=True, description="息税折旧摊销前利润"),
        "dtprofit_to_profit": Field(float, required=True, description="扣非净利润/净利润"),
        "profit_dedt": Field(float, required=True, description="净利润/扣非净利润"),
        "or_yoy": Field(float, required=True, description="营业收入同比增长率(%)"),
        "netprofit_yoy": Field(float, required=True, description="净利润同比增长率(%)"),
        "basic_eps_yoy": Field(float, required=True, description="每股收益同比增长率(%)"),
        "dt_eps_yoy": Field(float, required=True, description="稀释每股收益同比增长率(%)"),
        "tr_yoy": Field(float, required=True, description="营业总收入同比增长率(%)"),
        "netdebt": Field(float, required=True, description="净债务"),
        "debt_to_eqt": Field(float, required=True, description="产权比率"),
        "debt_to_assets": Field(float, required=True, description="资产负债率"),
        "interestdebt": Field(float, required=True, description="带息债务"),
        "assets_to_eqt": Field(float, required=True, description="权益乘数"),
        "quick_ratio": Field(float, required=True, description="速动比率"),
        "current_ratio": Field(float, required=True, description="流动比率"),
        "ar_turn": Field(float, required=True, description="应收账款周转率"),
        "bps": Field(float, required=True, description="每股净资产"),
        "ocfps": Field(float, required=True, description="每股经营活动产生的现金流量净额"),
        "fcff": Field(float, required=True, description="企业自由现金流量"),
        "fcfe": Field(float, required=True, description="股东自由现金流量"),
    }
)
