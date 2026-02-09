"""
Adj Factor Event Handler 配置。绑定表 sys_adj_factor_events。

特点：每只股票全量替换（delete + save），非增量；daily 跑一次检查所有股票。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_adj_factor_events",
    # immediate 模式：每个结果单独处理，避免 batch 中 1 个全量保存（qfq_kline 30s）阻塞整批 20 个
    # 否则中断时大量结果尚未执行 save，下次 run 仍会重复
    "save_mode": "immediate",
    "save_batch_size": 1,
    "ignore_fields": ["id", "event_date", "factor", "qfq_diff", "last_update"],
    "renew": {
        "type": "refresh",
        "last_update_info": {
            "date_field": "last_update",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "renew_if_over_days": {
            "value": 1,
        },
        "job_execution": {
            "list": "stock_list",
            "key": "id",
        },
    },
    "apis": {
        "adj_factor": {
            "provider_name": "tushare",
            "method": "get_adj_factor",
            "max_per_minute": 1500,
            "params_mapping": {
                "ts_code": "id",
            },
        },
        "daily_kline": {
            "provider_name": "tushare",
            "method": "get_daily_kline",
            "max_per_minute": 700,
            "params_mapping": {
                "ts_code": "id",
            },
        },
        "qfq_kline": {
            "provider_name": "akshare",
            "method": "get_qfq_kline",
            "max_per_minute": 80,
            "params_mapping": {
                "symbol": "id",  # handler 转为 sz000001/sh600000（AKShare stock_zh_a_hist_tx）
            },
        },
    },
}
