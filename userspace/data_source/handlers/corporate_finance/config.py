"""
Corporate Finance Handler 配置。绑定表 sys_corporate_finance。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_corporate_finance",
    "save_mode": "batch",  # 批量保存：累计 save_batch_size 个 bundle 后保存
    "save_batch_size": 20,  # 每20个bundle保存一次
    "ignore_fields": ["id", "quarter"],  # 这些字段由 handler 手动添加，不在 field_mapping 中
    "renew": {
        "type": "rolling",
        "rolling": {
            "unit": DateUtils.PERIOD_QUARTER,
            "length": 3,
        },
        "last_update_info": {
            "date_field": "quarter",
            "date_format": DateUtils.PERIOD_QUARTER,
        },
        "result_group_by": {
            "list": "stock_list",
            "key": "id",
        },
    },
    "apis": {
        "finance_data": {
            "provider_name": "tushare",
            "method": "get_finance_data",
            "max_per_minute": 500,
            "group_by": "ts_code",
            "field_mapping": {
                # 盈利能力指标
                "eps": "eps",
                "dt_eps": "dt_eps",
                "roe": "roe",
                "roe_dt": "roe_dt",
                "roa": "roa",
                "netprofit_margin": "netprofit_margin",
                "gross_profit_margin": "grossprofit_margin",  # API字段名差异
                "op_income": "op_income",
                "roic": "roic",
                "ebit": "ebit",
                "ebitda": "ebitda",
                "dtprofit_to_profit": "dtprofit_to_profit",
                "profit_dedt": "profit_dedt",
                # 成长能力指标
                "or_yoy": "or_yoy",
                "netprofit_yoy": "netprofit_yoy",
                "basic_eps_yoy": "basic_eps_yoy",
                "dt_eps_yoy": "dt_eps_yoy",
                "tr_yoy": "tr_yoy",
                # 偿债能力指标
                "netdebt": "netdebt",
                "debt_to_eqt": "debt_to_eqt",
                "debt_to_assets": "debt_to_assets",
                "interestdebt": "interestdebt",
                "assets_to_eqt": "assets_to_eqt",
                "quick_ratio": "quick_ratio",
                "current_ratio": "current_ratio",
                # 运营能力指标
                "ar_turn": "ar_turn",
                # 资产状况指标
                "bps": "bps",
                # 现金流指标
                "ocfps": "ocfps",
                "fcff": "fcff",
                "fcfe": "fcfe",
                # 日期字段（用于转换为 quarter）
                "end_date": "end_date",
            },
        },
    },
}
