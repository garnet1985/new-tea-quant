"""
Shibor Handler 配置。绑定表 sys_shibor。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_shibor",
    "save_mode": "unified",  # 统一保存：所有数据在 _do_save 中统一保存
    "renew": {
        "type": "rolling",
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "rolling": {
            "unit": DateUtils.PERIOD_DAY,
            "length": 30,
        },
    },
    "apis": {
        "shibor_data": {
            "provider_name": "tushare",
            "method": "get_shibor",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "date",
                "one_night": "on",
                "one_week": "1w",
                "one_month": "1m",
                "three_month": "3m",
                "one_year": "1y",
            },
            "params": {},
        },
    },
}
