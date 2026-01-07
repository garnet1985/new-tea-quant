from app.core.global_enums.enums import KlineTerm, AdjustType
from app.core.conf.conf import data_default_start_date

# ML增强版本设置 - 基于机器学习验证的重要参数
settings = {
    # 策略启用状态
    "is_enabled": False,  # V21.0 ML增强版本启用
    "name": "ReverseTrendBet",
    "description": "反转趋势策略 - 基于机器学习验证的重要参数",
    
    "key": "RTB",
    "version": "V25.0_Script_Optimized",
    
    "core": {
        "convergence": {
            "days": 15,  # 基于ML分析的收敛期
        },
        "stability": {
            "days": 8,   # 基于ML分析的稳定期
        },
        "invest_range": {
            "lower_bound": 0.008,  # 基于ML分析的买入区间
            "upper_bound": 0.008,
        },
        
        # 基于机器学习验证的重要参数阈值
        "thresholds": {
            # 1. 市值筛选条件 (基于脚本分析优化)
            "market_cap": {
                "max": 1800000,  # 市值 < 180万 (万元)
                "preference_max": 3000000,  # 优先小盘股：市值 < 300亿
            },
            
            # 2. PE比率筛选 (基于脚本分析优化)
            "pe_ratio": {
                "min": 2,    # PE > 2
                "max": 120,  # PE < 120
                "preference_min": 10,   # 优先范围 min
                "preference_max": 100,  # 优先范围 max
            },
            
            # 3. PB比率筛选 (基于脚本分析优化)
            "pb_ratio": {
                "min": 0.1,  # PB > 0.1
                "max": 7.5,  # PB < 7.5
                "preference_min": 0.3,  # 优先范围 min
                "preference_max": 8.0,  # 优先范围 max
            },
            
            # 4. PS比率筛选
            "ps_ratio": {
                "preference_min": 0.5,   # 优先范围 min
                "preference_max": 15.0,  # 优先范围 max
            },
            
            # 5. RSI条件 (基于脚本分析优化)
            "rsi": {
                "min": 7,    # RSI > 7
                "max": 92,   # RSI < 92
                "preference_min": 20,  # 优先范围 min
                "preference_max": 70,  # 优先范围 max
            },
            
            # 6. 价格历史分位数 (基于脚本分析优化)
            "price_percentile": {
                "min": 0.00,  # 价格分位数 > 0%
                "max": 0.95,  # 价格分位数 < 95%
                "preference_min": 0.2,  # 优先范围 min
                "preference_max": 0.6,  # 优先范围 max
            },
            
            # 7. 波动率条件 (基于脚本分析优化) - 最高权重 (0.106)
            "volatility": {
                "min": 0.007,  # 波动率 > 0.7%
                "max": 0.450,  # 波动率 < 45%
                "preference_min": 0.02,  # 优先范围: > 2%
                "preference_max": 0.15,  # 优先范围: < 15%
                "weight": 0.106
            },
            
            # 8. 成交量条件 (基于脚本分析优化)
            "volume_ratio_before": {
                "min": 0.7,  # 反转前成交量放大 ≥ 0.7倍
                "preference_min": 1.2,  # 优先: ≥ 1.2倍
                "weight": 0.042
            },
            "volume_ratio_after": {
                "min": 0.7,  # 反转后成交量放大 ≥ 0.7倍
                "preference_min": 1.5,  # 优先: ≥ 1.5倍
                "weight": 0.080
            },
            
            # 9. 均线收敛度条件 (基于脚本分析优化)
            "ma_convergence": {
                "max": 0.225,  # 均线收敛度 < 22.5%
                "preference_max": 0.05,  # 优先: < 5%
                "weight": 0.056
            },
            
            # 10. 价格相对均线位置条件 (基于脚本分析优化)
            "price_vs_ma20": {
                "min": -0.22,  # 价格与MA20距离 > -22%
                "max": 0.22,   # 价格与MA20距离 < 22%
                "preference_min": -0.05,  # 优先范围 min
                "preference_max": 0.05,   # 优先范围 max
                "weight": 0.046
            },
            "price_vs_ma60": {
                "min": -0.30,  # 价格与MA60距离 > -30%
                "max": 0.30,   # 价格与MA60距离 < 30%
                "preference_min": -0.08,  # 优先范围 min
                "preference_max": 0.08,   # 优先范围 max
                "weight": 0.044
            },
            
            # 11. 月线跌幅条件 (基于脚本分析优化)
            "monthly_drop_rate": {
                "min": 0.007,  # 月线跌幅 > 0.7%
                "max": 1.050,  # 月线跌幅 < 105%
                "preference_min": 0.05,  # 优先: > 5%
                "preference_max": 0.40,  # 优先: < 40%
                "weight": 0.044
            },
            
            # 12. 均线斜率条件 (基于脚本分析优化)
            "ma20_slope": {
                "min": -0.075,  # MA20斜率 > -7.5%
                "preference_min": -0.01,  # 优先: 不显著向下
                "weight": 0.038
            },
        },
    },

    # 模拟配置
    "simulation": {
        "start_date": data_default_start_date,
        "end_date": "",
        "sampling_amount": 100,  # ML分析使用500股票样本
        "record_summary": True,
        "analysis": True,
        "sampling": {
            "strategy": "uniform",  # 均匀间隔采样，默认策略
            "uniform": {
                "description": "均匀间隔采样 - 每间隔N个股票抽取一个，结果可重现"
            }
        }
    },

    # 数据要求配置 - ML增强版本
    "klines": {
        "terms": [KlineTerm.DAILY.value, KlineTerm.WEEKLY.value],
        "signal_base_term": KlineTerm.WEEKLY.value,  # 基于周线检测信号
        "simulate_base_term": KlineTerm.DAILY.value,  # 基于日线执行
        "min_required_base_records": 100,
        "adjust": AdjustType.QFQ.value,
        "indicators": {
            "moving_average": {
                "periods": [5, 10, 20, 60],  # ML分析中的重要均线
            },
            "rsi": {
                "period": 14,  # ML分析中的RSI周期
            },
        },
        "stock_labels": True
    },


    # 投资目标设置
    "goal": {
        "expiration": {
            "fixed_period": 200,
            "is_trading_period": True,
        },

        # 动态止损
        "dynamic_loss": {
            "ratio": -0.12,  # ML分析优化：-12%动态止损
            "close_invest": True
        },

        # ML增强版止损目标设置
        "stop_loss": {
            "stages": [
                {
                    "name": "loss15%",
                    "ratio": -0.15,  # ML分析优化：-15%止损
                    "close_invest": True
                }
            ]
        },
        
        # ML增强版止盈目标设置
        "take_profit": {
            "stages": [
                {
                    "name": "win20%",
                    "ratio": 0.2,  # 第一阶段：20%止盈
                    "sell_ratio": 0.4,  # 40%平仓
                },
                {
                    "name": "win30%",
                    "ratio": 0.3,  # 第二阶段：30%止盈
                    "sell_ratio": 0.4,  # 再平仓40%（累计80%）
                    "actions": ["set_dynamic_loss"]  # 设置动态止损控制剩余仓位
                }
                # 最后20%仓位由动态止损控制，可以无限上涨
            ]
        },
    },
    
    # 黑名单设置
    "blacklist": {
        "count": 0,
        "description": "ML增强版本：基于机器学习分析的黑名单",
        "list": []
    },
}
