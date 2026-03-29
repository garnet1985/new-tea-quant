from core.global_enums.enums import EntityType, AdjustType

settings = {
    # ========================================
    # 策略基本信息
    # ========================================
    "name": "momentum",
    "description": "动量策略：短期均价相对中期均价走强时触发机会",
    "is_enabled": True,

    # ========================================
    # 策略核心参数
    # ========================================
    "core": {
        # 动量 = (近20日均价 - 前40日均价) / 前40日均价，超过阈值则视为有机会
        "momentum_threshold": 0.05,
        # 与 worker 中窗口一致（20+40）；仅作文档/校验参考
        "lookback_days": 60,
        # 以下为 legacy simulate_opportunity 使用的简易止盈止损（收益率，非 goal 引擎）
        "simulate_stop_loss_ratio": -0.05,
        "simulate_take_profit_ratio": 0.10,
        "simulate_max_holding_days": 20,
    },

    # ========================================
    # 数据配置
    # ========================================
    "data": {
        "base_price_source": EntityType.STOCK_KLINE_DAILY.value,
        "adjust_type": AdjustType.QFQ.value,
        # 动量计算至少需要 60 根 K 线
        "min_required_records": 60,
        "indicators": {},
        "extra_data_sources": [],
    },

    # ========================================
    # 投资目标（与框架枚举/模拟器一致）
    # ========================================
    "goal": {
        "expiration": {
            "fixed_window_in_days": 30,
            "is_trading_days": True,
        },
        "stop_loss": {
            "stages": [
                {
                    "name": "loss10%",
                    "ratio": -0.1,
                    "close_invest": True,
                }
            ]
        },
        "take_profit": {
            "stages": [
                {
                    "name": "win10%",
                    "ratio": 0.1,
                    "sell_ratio": 0.5,
                },
                {
                    "name": "win20%",
                    "ratio": 0.2,
                    "close_invest": True,
                },
            ]
        },
    },

    # ========================================
    # 股票采样
    # ========================================
    "sampling": {
        "strategy": "continuous",
        "sampling_amount": 20,
    },

    # ========================================
    # 枚举器
    # ========================================
    "enumerator": {
        "use_sampling": False,
        "max_test_versions": 3,
        "max_output_versions": 2,
        "max_workers": "auto",
        "is_verbose": True,
        "memory_budget_mb": "auto",
        "warmup_batch_size": "auto",
        "min_batch_size": "auto",
        "max_batch_size": "auto",
        "monitor_interval": 5,
    },

    # ========================================
    # 交易成本
    # ========================================
    "fees": {
        "commission_rate": 0.00025,
        "min_commission": 5.0,
        "stamp_duty_rate": 0.001,
        "transfer_fee_rate": 0.0,
    },

    # ========================================
    # 价格因子模拟器
    # ========================================
    "price_simulator": {
        "use_sampling": False,
        "max_workers": "auto",
        "base_version": "latest",
    },

    # ========================================
    # 资金分配模拟器
    # ========================================
    "capital_simulator": {
        "use_sampling": False,
        "base_version": "latest",
        "initial_capital": 1_000_000,
        "allocation": {
            "mode": "equal_capital",
            "max_portfolio_size": 10,
            "max_weight_per_stock": 0.3,
            "lot_size": 100,
            "lots_per_trade": 1,
            "kelly_fraction": 0.5,
        },
        "output": {
            "save_trades": True,
            "save_equity_curve": True,
        },
    },

    # ========================================
    # 扫描器
    # ========================================
    "scanner": {
        "max_workers": "auto",
        "adapters": ["console"],
    },
}
