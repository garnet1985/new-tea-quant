"""
Corporate Finance Handler 配置。绑定表 sys_corporate_finance。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_corporate_finance",
    "save_mode": "batch",
    "save_batch_size": 100,
    "ignore_fields": ["id", "quarter"],
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
        "job_execution": {
            "list": "stock_list",
            "key": "id",
        },
    },
    "apis": {
        "finance_data": {
            "provider_name": "tushare",
            "method": "get_finance_data",
            "max_per_minute": 500,
            "params_mapping": {
                "ts_code": "id",
            },
            "result_mapping": {
                "eps": "eps",
                "dt_eps": "dt_eps",
                "roe": "roe",
                "roe_dt": "roe_dt",
                "roa": "roa",
                "netprofit_margin": "netprofit_margin",
                "gross_profit_margin": "grossprofit_margin",
                "op_income": "op_income",
                "roic": "roic",
                "ebit": "ebit",
                "ebitda": "ebitda",
                "dtprofit_to_profit": "dtprofit_to_profit",
                "profit_dedt": "profit_dedt",
                "or_yoy": "or_yoy",
                "netprofit_yoy": "netprofit_yoy",
                "basic_eps_yoy": "basic_eps_yoy",
                "dt_eps_yoy": "dt_eps_yoy",
                "tr_yoy": "tr_yoy",
                "netdebt": "netdebt",
                "debt_to_eqt": "debt_to_eqt",
                "debt_to_assets": "debt_to_assets",
                "interestdebt": "interestdebt",
                "assets_to_eqt": "assets_to_eqt",
                "quick_ratio": "quick_ratio",
                "current_ratio": "current_ratio",
                "ar_turn": "ar_turn",
                "bps": "bps",
                "ocfps": "ocfps",
                "fcff": "fcff",
                "fcfe": "fcfe",
                "end_date": "end_date",
            },
        },
    },
}
