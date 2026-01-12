from app.core.global_enums.enums import EntityType, AdjustType

settings = {
    # ========================================
    # 策略基本信息
    # ========================================
    
    # 策略唯一名字，程序中的 key
    "name": "example",
    
    # 策略描述
    "description": "Example momentum strategy with technical indicators",
    
    # 策略是否启用
    "is_enabled": False,
    
    # ========================================
    # 策略核心参数
    # ========================================
    "core": {
        # 随机种子（用于保证结果可复现，即使策略逻辑是确定性的）
        # 注意：当前策略逻辑是确定性的（均线突破），不需要随机数
        # 但为了测试和未来扩展，保留此配置
        "random_seed": 42,
        
        # 你的策略特有参数
        # 例如：
        # "momentum_threshold": 0.05,
        # "volume_multiplier": 1.5,
    },
    
    # ========================================
    # 数据配置
    # ========================================
    "data": {
        # 基础 K 线配置
        "base": EntityType.STOCK_KLINE_DAILY.value,
        
        # 复权方式
        "adjust": AdjustType.QFQ.value,
        
        # 最小要求的基础周期记录数
        "min_required_records": 1000,
        
        # ========================================
        # 技术指标配置（框架自动计算）
        # ========================================
        "indicators": {
            # 移动平均线（可配置多个周期）
            "ma": [
                {"period": 5},
                {"period": 10},
                {"period": 20},
                {"period": 60}
            ],
            
            # 指数移动平均线
            "ema": [
                {"period": 12},
                {"period": 26}
            ],
            
            # RSI 指标
            "rsi": [
                {"period": 14}
            ],
            
            # MACD 指标
            "macd": [
                {"fast": 12, "slow": 26, "signal": 9}
            ],
            
            # 布林带指标
            "bbands": [
                {"period": 20, "std": 2.0}
            ],
            
            # ATR 指标（真实波动幅度）
            "atr": [
                {"period": 14}
            ]
        },
        
        # ========================================
        # 外部数据依赖
        # ========================================
        "required_entities": [
            {
                "type": EntityType.GDP.value,
            },
            {
                "type": EntityType.TAG_SCENARIO.value,
                "name": "momentum_mid_term"
            }
        ]
    },
    
    # ========================================
    # 股票采样配置
    # ========================================
    "sampling": {
        # 采样策略类型
        "strategy": "pool",  # uniform / stratified / random / continuous / pool / blacklist
        
        # 采样数量
        "sampling_amount": 50,
        
        # ========================================
        # 各采样策略的专用配置
        # ========================================
        
        # 均匀采样
        "uniform": {
            "description": "均匀间隔采样 - 每间隔 N 个股票抽取一个，结果可重现"
        },
        
        # 分层采样
        "stratified": {
            "seed": 42,
            "description": "分层采样 - 按市场类型（沪深主板，中小板，创业板，科创板）采样，科学合理"
        },
        
        # 随机采样
        "random": {
            "seed": 42,
            "description": "随机采样 - 随机抽取指定数量的股票"
        },
        
        # 连续采样
        "continuous": {
            "start_idx": 0,
            "description": "连续采样 - 从 start_idx 开始连续取指定数量的股票"
        },
        
        # 股票池采样
        "pool": {
            # 方式 1：文件路径（推荐：长列表、易迁移）
            "id_list_path": "../pools/high_quality_stocks.txt",
            
            # 方式 2：直接数组（推荐：短列表、快速测试）
            # "stock_pool": ["000001.SZ", "000002.SZ", "000333.SZ"],
            
            # 说明：如果两个都配置，优先使用 id_list_path
            "description": "股票池采样 - 从指定股票池中抽取"
        },
        
        # 黑名单采样
        "blacklist": {
            # 方式 1：文件路径（推荐）
            "id_list_path": "../blacklists/st_stocks.txt",
            
            # 方式 2：直接数组（备选）
            # "blacklist": ["ST*", "退市*"],
            
            "description": "黑名单采样 - 排除黑名单后抽取"
        }
    },
    
    # ========================================
    # Simulator 配置
    # ========================================
    "simulator": {
        # 回测时间范围
        "start_date": "20230101",  # 空字符串 = 使用默认开始日期
        "end_date": "",            # 空字符串 = 到最新记录
        
        # ========================================
        # 投资目标设置（止盈止损）
        # ========================================
        "goal": {
            # 到期平仓（可选）
            "expiration": {
                "fixed_period": 30,           # 持仓天数
                "is_trading_period": True     # True = 交易日，False = 自然日
            },
            
            # 保本止损（可选）
            "protect_loss": {
                "ratio": 0,                   # 回到成本价
                "close_invest": True          # 触发时清仓
            },
            
            # 动态止损（可选）
            "dynamic_loss": {
                "ratio": -0.1,                # 从最高点回撤 10%
                "close_invest": True          # 触发时清仓
            },
            
            # 分段止损
            "stop_loss": {
                "stages": [
                    {
                        "name": "loss20%",
                        "ratio": -0.2,        # 亏损 20%
                        "sell_ratio": 0.5     # 卖出 50%
                    },
                    {
                        "name": "loss30%",
                        "ratio": -0.3,        # 亏损 30%
                        "close_invest": True  # 清仓
                    }
                ]
            },
            
            # 分段止盈
            "take_profit": {
                "stages": [
                    {
                        "name": "win10%",
                        "ratio": 0.1,                      # 盈利 10%
                        "sell_ratio": 0.2,                 # 卖出 20%
                        "actions": ["set_protect_loss"]    # 启动保本止损
                    },
                    {
                        "name": "win20%",
                        "ratio": 0.2,
                        "sell_ratio": 0.2
                    },
                    {
                        "name": "win30%",
                        "ratio": 0.3,
                        "sell_ratio": 0.2,
                        "actions": ["set_dynamic_loss"]    # 启动动态止损
                    }
                ]
            }
        }
    },
    
    # ========================================
    # 性能配置
    # ========================================
    "performance": {
        "max_workers": "auto"  # "auto" / 数字（进程数）
    }
}
