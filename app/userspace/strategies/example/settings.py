from app.core.global_enums.enums import EntityType, AdjustType

settings = {
    # ========================================
    # 策略基本信息
    # ========================================
    "name": "example",
    "description": "Example RSI oversold strategy (minimal settings)",
    "is_enabled": True,

    # ========================================
    # 策略核心参数（仅示例策略真正需要的字段）
    # ========================================
    "core": {
        # 超卖阈值
        "rsi_oversold_threshold": 20,
    },

    # ========================================
    # 数据配置（仅保留枚举器 / 模拟器真正需要的字段）
    # ========================================
    "data": {
        # 基础 K 线配置
        "base": EntityType.STOCK_KLINE_DAILY.value,
        # 复权方式
        "adjust": AdjustType.QFQ.value,
        # 最小要求的基础周期记录数（用于 lookback）
        "min_required_records": 200,

        # 仅计算本策略需要的 RSI 指标
        "indicators": {
            "rsi": [
                {"period": 14}
            ]
        },

        # 本示例不依赖任何外部实体数据
        "required_entities": []
    },

    # ========================================
    # 股票采样配置（示例：固定池中采样少量股票）
    # ========================================
    "sampling": {
        "strategy": "pool",
        "sampling_amount": 2,
        "pool": {
            # 直接在配置中给出一个很小的股票池，方便快速测试
            "stock_pool": ["000001.SZ", "000002.SZ"],
        }
    },

    # ========================================
    # Simulator / Enumerator 共用的目标配置（止盈止损）
    # 示例保留一份非常简化的 goal 配置，方便演示
    # ========================================
    "simulator": {
        "start_date": "20230101",
        "end_date": "",
        "goal": {
            # 简单的到期平仓
            "expiration": {
                "fixed_period": 30,
                "is_trading_period": True
            }
        }
    },

    # ========================================
    # 性能配置（保留 max_workers，其他细节走全局 auto 逻辑）
    # ========================================
    "performance": {
        "max_workers": "auto"
    }
}
