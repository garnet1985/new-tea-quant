"""
CPI Handler 配置。绑定表 sys_cpi。
"""
from core.utils.date.date_utils import DateUtils


CONFIG = {
    "table": "sys_cpi",
    "save_mode": "unified",  # 统一保存：所有数据在 _do_save 中统一保存
    "renew": {
        "type": "rolling",
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_MONTH,
        },
        "rolling": {
            "unit": DateUtils.PERIOD_MONTH,
            "length": 12,
        },
    },
    "apis": {
        "cpi_data": {
            "provider_name": "tushare",
            "method": "get_cpi",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "month",
                "cpi": "nt_val",
                "cpi_yoy": "nt_yoy",
                "cpi_mom": "nt_mom",
            },
            "params": {},
        },
    },
}
