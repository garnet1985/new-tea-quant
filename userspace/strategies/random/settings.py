from core.global_enums.enums import EntityType, AdjustType

settings = {
    # ========================================
    # 策略基本信息
    # ========================================
    "name": "random",
    "description": "Random strategy for testing (fixed random seed for reproducibility)",
    # 参与扫描/模拟列表时需为 True
    "is_enabled": True,

    # ========================================
    # 策略核心参数
    # ========================================
    "core": {
        "random_seed": 42,
        # 发现机会的概率（0.0 ~ 1.0）
        "probability": 0.1,
    },

    # ========================================
    # 数据配置
    # ========================================
    "data": {
        "base_price_source": EntityType.STOCK_KLINE_DAILY.value,
        "adjust_type": AdjustType.QFQ.value,
        "min_required_records": 100,
        "indicators": {
            "ma": [
                {"period": 5},
                {"period": 10},
            ]
        },
        "extra_data_sources": [],
    },

    # ========================================
    # 股票采样（strategy=random 与 core.random_seed 独立；此处控制股票子集）
    # ========================================
    "sampling": {
        "strategy": "random",
        "sampling_amount": 50,
        "random": {
            "seed": 42,
        },
    },

    # ========================================
    # 投资目标（止盈止损等）
    # ========================================
    "goal": {
        "expiration": {
            "fixed_window_in_days": 30,
            "is_trading_days": True,
        },
        # "protect_loss": {
        #     "ratio": 0,
        #     "close_invest": True,
        # },
        "dynamic_loss": {
            "ratio": -0.1,
            "close_invest": True,
        },
        "stop_loss": {
            "stages": [
                {
                    "name": "loss20%",
                    "ratio": -0.2,
                    "sell_ratio": 0.5,
                }
            ]
        },
        "take_profit": {
            "stages": [
                {
                    "name": "win30%",
                    "ratio": 0.3,
                    "sell_ratio": 0.5,
                    "actions": ["set_dynamic_loss"],
                },
            ]
        },
    },

    # ========================================
    # 枚举器
    # ========================================
    "enumerator": {
        # True: 按 sampling 做子集枚举，结果在 results/.../test/
        # False: 全市场枚举，结果在 results/.../output/
        "use_sampling": False,
        "max_test_versions": 3,
        "max_output_versions": 2,
        "max_workers": "auto",
        "is_verbose": False,
        "memory_budget_mb": "auto",
        "warmup_batch_size": "auto",
        "min_batch_size": "auto",
        "max_batch_size": "auto",
        "monitor_interval": 5,
    },

    # ========================================
    # 交易成本（可被模拟器局部覆盖）
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
        # True: 与 enumerator use_sampling=True 一致时用 test/；全量时改为 False
        "use_sampling": False,
        "max_workers": "auto",
        "base_version": "latest",
        # 可选；空则走枚举结果时间范围或框架默认
        # "start_date": "20230101",
        # "end_date": "",
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
