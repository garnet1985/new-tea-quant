"""
GDP Handler 配置。绑定表 sys_gdp。
"""
from core.utils.date.date_utils import DateUtils


CONFIG = {
    "table": "sys_gdp",
    "save_mode": "unified",  # 统一保存：所有数据在 _do_save 中统一保存
    "renew": {
        "type": "rolling",
        "last_update_info": {
            "date_field": "quarter",
            # 使用标准周期 key，由 DateUtils 统一处理为 YYYYMMQn
            "date_format": DateUtils.PERIOD_QUARTER,
        },
        "rolling": {
            "unit": DateUtils.PERIOD_QUARTER,
            "length": 4,
        },
    },
    "apis": {
        "gdp_data": {
            "provider_name": "tushare",
            "method": "get_gdp",
            "max_per_minute": 200,
            "field_mapping": {
                "quarter": "quarter",
                "gdp": "gdp",
                "gdp_yoy": "gdp_yoy",
                "primary_industry": "pi",
                "primary_industry_yoy": "pi_yoy",
                "secondary_industry": "si",
                "secondary_industry_yoy": "si_yoy",
                "tertiary_industry": "ti",
                "tertiary_industry_yoy": "ti_yoy",
            },
            "params": {},
        },
    },
}
