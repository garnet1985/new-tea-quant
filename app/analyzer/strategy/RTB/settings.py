from app.data_source.enums import KlineTerm, AdjustType
from app.conf.conf import data_default_start_date

# ML增强版本设置 - 基于机器学习验证的重要参数
settings = {
    # 策略启用状态
    "is_enabled": False,  # V21.0 ML增强版本启用

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
    },

    # 模拟配置
    "simulation": {
        "start_date": data_default_start_date,
        "end_date": "",
        "sampling_amount": 500,  # ML分析使用500股票样本
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


    # ML增强版投资目标设置
    "goal": {
        "fixed_trading_days": 200,

        "is_customized": False,

        # ML增强版止损目标设置
        "stop_loss": {
            "dynamic": {
                "name": "dynamic",
                "ratio": -0.12,  # ML分析优化：-12%动态止损
                "close_invest": True
            },
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
                    "set_stop_loss": "dynamic"  # 设置动态止损控制剩余仓位
                }
                # 最后20%仓位由动态止损控制，可以无限上涨
            ]
        },

        # 黑名单设置
        "blacklist": {
            "count": 0,
            "description": "ML增强版本：基于机器学习分析的黑名单",
            "list": []
        }
    },

    # ML增强版核心参数阈值设置
    "ml_enhanced": {
        # 基于机器学习验证的重要参数阈值
        "thresholds": {
            # 最高权重参数 (0.106)
            "volatility": {
                "min": 0.02,  # 波动率 > 2%
                "max": 0.15,  # 波动率 < 15%
                "weight": 0.106
            },
            
            # 第二重要参数 (0.080)
            "volume_ratio_after": {
                "min": 1.5,   # 反转后成交量放大 ≥ 1.5倍
                "weight": 0.080
            },
            
            # 中高权重参数 (0.056)
            "ma_convergence": {
                "max": 0.05,  # 均线收敛度 < 5%
                "weight": 0.056
            },
            
            # 中等权重参数 (0.053-0.045)
            "price_vs_ma20": {
                "min": -0.05,  # 价格与MA20距离在±5%内
                "max": 0.05,
                "weight": 0.046
            },
            "price_vs_ma60": {
                "min": -0.08,  # 价格与MA60距离在±8%内
                "max": 0.08,
                "weight": 0.044
            },
            
            # 月线跌幅参数 (0.044)
            "monthly_drop_rate": {
                "min": 0.05,  # 月线跌幅 > 5%
                "max": 0.40,  # 月线跌幅 < 40%
                "weight": 0.044
            },
            
            # 均线斜率参数
            "ma20_slope": {
                "min": -0.01,  # MA20斜率不显著向下
                "weight": 0.038
            },
            
            # RSI参数
            "rsi": {
                "min": 20,    # RSI > 20
                "max": 70,    # RSI < 70
                "weight": 0.038
            },
            
            # 价格分位数参数
            "price_percentile": {
                "min": 0.2,   # 价格分位数 > 20%
                "max": 0.6,   # 价格分位数 < 60%
                "weight": 0.016
            },
            
            # 成交量确认参数
            "volume_ratio_before": {
                "min": 1.2,   # 反转前成交量放大 ≥ 1.2倍
                "weight": 0.042
            }
        },
        
        # 财务筛选参数（基于市值效应分析）
        "financial_filters": {
            "market_cap": {
                "max": 3000000,  # 优先小盘股：市值 < 300亿
                "preference": "small_cap"  # 小盘股成功率89.1% > 大盘股86.6%
            },
            "pe_ratio": {
                "min": 10,
                "max": 100
            },
            "pb_ratio": {
                "min": 0.3,
                "max": 8.0
            },
            "ps_ratio": {
                "min": 0.5,
                "max": 15.0
            }
        },
        
        # 关键成功指标阈值
        "success_indicators": {
            "volume_surge_after_threshold": 1.5,    # 反转后成交量放大阈值
            "volume_surge_before_threshold": 1.2,   # 反转前成交量放大阈值
            "ma_convergence_threshold": 0.05,       # 均线收敛度阈值
            "volatility_optimal_range": [0.02, 0.15],  # 最优波动率范围
        }
    }
}
