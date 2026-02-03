"""
PPI Handler 配置。绑定表 sys_ppi。
"""
from core.utils.date.date_utils import DateUtils


CONFIG = {
    "table": "sys_ppi",
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
        "ppi_data": {
            "provider_name": "tushare",
            "method": "get_ppi",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "month",
                "ppi": "ppi_accu",
                "ppi_yoy": "ppi_yoy",
                "ppi_mom": "ppi_mom",
            },
            "params": {},
        },
    },
}
