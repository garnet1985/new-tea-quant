"""
LPR Handler 配置。绑定表 sys_lpr。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_lpr",
    "save_mode": "unified",  # 统一保存：所有数据在 _do_save 中统一保存
    "renew": {
        "type": "rolling",
        "rolling": {
            "length": 30,
            "unit": DateUtils.PERIOD_DAY,
        },
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_DAY,
        },
    },
    "apis": {
        "lpr_data": {
            "provider_name": "tushare",
            "method": "get_lpr",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "date",
                "lpr_1_y": "1y",
                "lpr_5_y": "5y",
            },
            "params": {},
        },
    },
}
