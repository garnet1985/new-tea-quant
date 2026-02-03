"""
PMI Handler 配置。绑定表 sys_pmi。
"""
from core.utils.date.date_utils import DateUtils


CONFIG = {
    "table": "sys_pmi",
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
        "pmi_data": {
            "provider_name": "tushare",
            "method": "get_pmi",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "MONTH",
                "pmi": "PMI010000",
                "pmi_l_scale": "PMI010100",
                "pmi_m_scale": "PMI010200",
                "pmi_s_scale": "PMI010300",
            },
            "params": {},
        },
    },
}
