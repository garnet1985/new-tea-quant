"""
data_corporate_finance 表结构定义（Python，变量名 schema）

企业财务数据。主键 id/quarter nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_corporate_finance",
    "primaryKey": ["id", "quarter"],
    "fields": [
        {"name": "id", "type": "varchar", "length": 16, "isRequired": True, "nullable": False, "description": "股票代码ts_code"},
        {"name": "quarter", "type": "varchar", "length": 16, "isRequired": True, "nullable": False, "description": "季度 YYYYQ[1-4]"},
        {"name": "eps", "type": "float", "isRequired": True, "nullable": True, "description": "每股收益"},
        {"name": "dt_eps", "type": "float", "isRequired": True, "nullable": True, "description": "稀释每股收益"},
        {"name": "roe_dt", "type": "float", "isRequired": True, "nullable": True, "description": "扣非净资产收益率"},
        {"name": "roe", "type": "float", "isRequired": True, "nullable": True, "description": "净资产收益率"},
        {"name": "roa", "type": "float", "isRequired": True, "nullable": True, "description": "总资产收益率"},
        {"name": "netprofit_margin", "type": "float", "isRequired": True, "nullable": True, "description": "销售净利率"},
        {"name": "gross_profit_margin", "type": "float", "isRequired": True, "nullable": True, "description": "毛利率"},
        {"name": "op_income", "type": "float", "isRequired": True, "nullable": True, "description": "经营活动净收益"},
        {"name": "roic", "type": "float", "isRequired": True, "nullable": True, "description": "投入资本回报率"},
        {"name": "ebit", "type": "float", "isRequired": True, "nullable": True, "description": "息税前利润"},
        {"name": "ebitda", "type": "float", "isRequired": True, "nullable": True, "description": "息税折旧摊销前利润"},
        {"name": "dtprofit_to_profit", "type": "float", "isRequired": True, "nullable": True, "description": "扣非净利/净利润"},
        {"name": "profit_dedt", "type": "float", "isRequired": True, "nullable": True, "description": "净利润/扣非净利润"},
        {"name": "or_yoy", "type": "float", "isRequired": True, "nullable": True, "description": "营业收入同比增长率(%)"},
        {"name": "netprofit_yoy", "type": "float", "isRequired": True, "nullable": True, "description": "净利润同比增长率(%)"},
        {"name": "basic_eps_yoy", "type": "float", "isRequired": True, "nullable": True, "description": "每股收益同比增长率(%)"},
        {"name": "dt_eps_yoy", "type": "float", "isRequired": True, "nullable": True, "description": "稀释每股收益同比增长率(%)"},
        {"name": "tr_yoy", "type": "float", "isRequired": True, "nullable": True, "description": "营业总收入同比增长率(%)"},
        {"name": "netdebt", "type": "float", "isRequired": True, "nullable": True, "description": "净债务"},
        {"name": "debt_to_eqt", "type": "float", "isRequired": True, "nullable": True, "description": "产权比率"},
        {"name": "debt_to_assets", "type": "float", "isRequired": True, "nullable": True, "description": "资产负债率"},
        {"name": "interestdebt", "type": "float", "isRequired": True, "nullable": True, "description": "带息债务"},
        {"name": "assets_to_eqt", "type": "float", "isRequired": True, "nullable": True, "description": "权益乘数"},
        {"name": "quick_ratio", "type": "float", "isRequired": True, "nullable": True, "description": "速动比率"},
        {"name": "current_ratio", "type": "float", "isRequired": True, "nullable": True, "description": "流动比率"},
        {"name": "ar_turn", "type": "float", "isRequired": True, "nullable": True, "description": "应收账款周转率"},
        {"name": "bps", "type": "float", "isRequired": True, "nullable": True, "description": "每股净资产"},
        {"name": "ocfps", "type": "float", "isRequired": True, "nullable": True, "description": "每股经营现金流净额"},
        {"name": "fcff", "type": "float", "isRequired": True, "nullable": True, "description": "企业自由现金流量"},
        {"name": "fcfe", "type": "float", "isRequired": True, "nullable": True, "description": "股东自由现金流量"},
    ],
}
