from core.global_enums.enums import EntityType, AdjustType

settings = {
    # ========================================
    # 策略基本信息
    # ========================================
    
    # 策略唯一名字，程序中的 key
    "name": "random",
    
    # 策略描述
    "description": "Random strategy for testing (with fixed random seed for reproducibility)",
    
    # 策略是否启用
    "is_enabled": False,  # 启用用于测试
    
    # ========================================
    # 策略核心参数
    # ========================================
    "core": {
        # 随机种子（保证结果可复现）
        "random_seed": 42,
        
        # 发现机会的概率（0.0 ~ 1.0）
        # 0.1 = 10% 概率发现机会
        "probability": 0.1
    },
    
    # ========================================
    # 数据配置
    # ========================================
    "data": {
        # 基础 K 线配置
        "base_price_source": EntityType.STOCK_KLINE_DAILY.value,
        
        # 复权方式
        "adjust_type": AdjustType.QFQ.value,
        
        # 最小要求的基础周期记录数
        "min_required_records": 100,
        
        # ========================================
        # 技术指标配置（框架自动计算）
        # ========================================
        "indicators": {
            # 移动平均线（简单配置，用于测试）
            "ma": [
                {"period": 5},
                {"period": 10}
            ]
        },
        
        # ========================================
        # 外部数据依赖（测试用，不需要）
        # ========================================
        "required_entities": []
    },
    
    # ========================================
    # 股票采样配置
    # ========================================
    "sampling": {
        # 采样策略类型
        "strategy": "random",  # 使用随机采样
        
        # 采样数量
        "sampling_amount": 50,
        
        # 随机采样配置
        "random": {
            "seed": 42,  # 随机种子
            "description": "随机采样 - 用于测试"
        }
    },
    
    # ========================================
    # 投资目标设置（止盈止损，顶层配置）
    # ========================================
    "goal": {
            # 到期平仓（可选）
            "expiration": {
                "fixed_window_in_days": 30,   # 持仓天数
                "is_trading_days": True       # True = 交易日，False = 自然日
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
    },
    
    # ========================================
    # Simulator 配置
    # ========================================
    "price_simulator": {
        # 回测时间范围
        "start_date": "20230101",  # 空字符串 = 使用默认开始日期
        "end_date": "",            # 空字符串 = 到最新记录
    },
    
    # ========================================
    # 性能配置
    # ========================================
    "performance": {
        "max_workers": "auto"  # "auto" / 数字（进程数）
    }
}
