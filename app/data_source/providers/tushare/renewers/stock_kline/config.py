"""
stock_kline（富含 daily_basic 字段）更新配置

表结构：
- 主键：id (股票代码), term (K线周期), date (交易日期)
- 数据来源：daily (K线数据) + daily_basic (基本面数据)
- 特点：需要合并两个API，并处理daily_basic的缺失值
"""

CONFIG = {
    'table_name': 'stock_kline',
    # renew_mode说明：
    # incremental = 业务逻辑上的增量（只加载最新记录做判断，内存占用小）
    # 保存时使用replace方法（支持幂等性，可重复运行）
    'renew_mode': 'incremental',
    
    'date': {
        'type': 'date',
        'field': 'date',
        'interval': 'day'
    },
    
    'job_mode': 'multithread',
    
    'multithread': {
        'workers': 10,  # 降低并发，减少限流压力
        'log': {
            'success': '✅ 股票 {stock_name} {id} [{term}] 更新完毕 - 进度 {progress}%',
            'failure': '❌ 股票 {stock_name} {id} [{term}] 更新失败'
        }
    },
    
    'rate_limit': {
        # 因为 daily_basic 限制为 700 次/分钟
        # daily, weekly, monthly 限制为 800 次/分钟
        # 保守配置600，避免瞬时并发压力
        'max_per_minute': 700
    },
    
    'apis': [
        # 注意：根据term不同，会动态选择使用daily/weekly/monthly中的一个
        {
            'name': 'daily',
            'method': 'daily',
            'params': {
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}',
                'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
            },
            'mapping': {
                'id': 'ts_code',
                'date': 'trade_date',
                'open': 'open',
                'highest': 'high',
                'lowest': 'low',
                'close': 'close',
                'pre_close': 'pre_close',
                'price_change_delta': 'change',
                'price_change_rate_delta': 'pct_chg',
                'volume': 'vol',
                'amount': 'amount'
            }
        },
        {
            'name': 'weekly',
            'method': 'weekly',
            'params': {
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}',
                'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
            },
            'mapping': {
                'id': 'ts_code',
                'date': 'trade_date',
                'open': 'open',
                'highest': 'high',
                'lowest': 'low',
                'close': 'close',
                'pre_close': 'pre_close',
                'price_change_delta': 'change',
                'price_change_rate_delta': 'pct_chg',
                'volume': 'vol',
                'amount': 'amount'
            }
        },
        {
            'name': 'monthly',
            'method': 'monthly',
            'params': {
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}',
                'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
            },
            'mapping': {
                'id': 'ts_code',
                'date': 'trade_date',
                'open': 'open',
                'highest': 'high',
                'lowest': 'low',
                'close': 'close',
                'pre_close': 'pre_close',
                'price_change_delta': 'change',
                'price_change_rate_delta': 'pct_chg',
                'volume': 'vol',
                'amount': 'amount'
            }
        },
        {
            'name': 'daily_basic',
            'method': 'daily_basic',
            'params': {
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}',
                'fields': 'ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv'
            },
            'mapping': {
                'id': 'ts_code',
                'date': 'trade_date',
                'turnover_rate': 'turnover_rate',
                'free_turnover_rate': 'turnover_rate_f',
                'volume_ratio': 'volume_ratio',
                'pe': 'pe',
                'pe_ttm': 'pe_ttm',
                'pb': 'pb',
                'ps': 'ps',
                'ps_ttm': 'ps_ttm',
                'dv_ratio': 'dv_ratio',
                'dv_ttm': 'dv_ttm',
                'total_share': 'total_share',
                'float_share': 'float_share',
                'free_share': 'free_share',
                'total_market_value': 'total_mv',
                'circ_market_value': 'circ_mv'
            }
        }
    ]
}



