"""
企业财务指标更新配置

使用Tushare的fina_indicator接口获取财务指标数据
"""

CONFIG = {
    'table_name': 'corporate_finance',
    'renew_mode': 'incremental',  # 增量更新（只请求需要的季度）
    'date_field': 'quarter',  # 使用quarter作为日期字段（格式：YYYYQ1-4）
    'renew_interval': 'quarter',  # 按季度更新
    
    'job_mode': 'multithread',
    'multithread': {
        'workers': 6,  # 降低并发，避免限流
        'log': {
            'success': '✅ 股票 {stock_name} {id} 财务数据更新完毕 - 进度 {progress}%',
            'failure': '❌ 股票 {stock_name} {id} 财务数据更新失败'
        }
    },
    
    'rate_limit': {
        'max_per_minute': 500,  # fina_indicator接口限制
    },
    
    # API配置
    'apis': [
        {
            'name': 'fina_indicator',
            'method': 'fina_indicator',
            'params': {
                'ts_code': '{ts_code}',
                'period': '{period}',  # 报告期，格式YYYYMMDD
                # 字段说明：
                # - 盈利能力指标
                # - 成长能力指标
                # - 偿债能力指标
                # - 运营能力指标
                # - 现金流指标
                # - 资产状况指标
                'fields': ','.join([
                    'ts_code', 'end_date', 'ann_date',
                    # 盈利能力
                    'eps', 'dt_eps', 'roe', 'roe_dt', 'roa',
                    'netprofit_margin', 'grossprofit_margin', 'op_income',
                    'roic', 'ebit', 'ebitda', 'dtprofit_to_profit', 'profit_dedt',
                    # 成长能力
                    'or_yoy', 'netprofit_yoy', 'basic_eps_yoy', 'dt_eps_yoy', 'tr_yoy',
                    # 偿债能力
                    'netdebt', 'debt_to_eqt', 'debt_to_assets', 'interestdebt',
                    'assets_to_eqt', 'quick_ratio', 'current_ratio',
                    # 运营能力
                    'ar_turn',
                    # 资产状况
                    'bps',
                    # 现金流
                    'ocfps', 'fcff', 'fcfe'
                ])
            },
            'mapping': {
                # 主键字段
                'ts_code': 'id',
                'end_date': '_end_date',  # 临时字段，转换为quarter后删除
                'ann_date': None,  # 不保存（公告日期）
                
                # 盈利能力指标（完全匹配，直接使用）
                'eps': 'eps',
                'dt_eps': 'dt_eps',
                'roe': 'roe',
                'roe_dt': 'roe_dt',
                'roa': 'roa',
                'netprofit_margin': 'netprofit_margin',
                'grossprofit_margin': 'gross_profit_margin',  # API字段名差异！
                'op_income': 'op_income',
                'roic': 'roic',
                'ebit': 'ebit',
                'ebitda': 'ebitda',
                'dtprofit_to_profit': 'dtprofit_to_profit',
                'profit_dedt': 'profit_dedt',
                
                # 成长能力指标
                'or_yoy': 'or_yoy',
                'netprofit_yoy': 'netprofit_yoy',
                'basic_eps_yoy': 'basic_eps_yoy',
                'dt_eps_yoy': 'dt_eps_yoy',
                'tr_yoy': 'tr_yoy',
                
                # 偿债能力指标
                'netdebt': 'netdebt',
                'debt_to_eqt': 'debt_to_eqt',
                'debt_to_assets': 'debt_to_assets',
                'interestdebt': 'interestdebt',
                'assets_to_eqt': 'assets_to_eqt',
                'quick_ratio': 'quick_ratio',
                'current_ratio': 'current_ratio',
                
                # 运营能力指标
                'ar_turn': 'ar_turn',
                
                # 资产状况指标
                'bps': 'bps',
                
                # 现金流指标
                'ocfps': 'ocfps',
                'fcff': 'fcff',
                'fcfe': 'fcfe'
            }
        }
    ]
}
