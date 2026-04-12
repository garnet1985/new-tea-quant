from core.modules.data_contract.contract_const import DataKey

settings = {
    # ========================================
    # 策略基本信息
    # ========================================
    "name": "example_activity_high",
    "description": "Example strategy gated by activity_high tag (activity-ratio20) + RSI oversold.",
    "is_enabled": True,

    # ========================================
    # 策略核心参数
    # ========================================
    "core": {
        # 超卖阈值
        "rsi_oversold_threshold": 20,
        # Tag 场景名：来自 userspace/tags/<scenario>/settings.py 中的 Settings["name"]
        "activity_tag_scenario": "activity-ratio20",
        # Tag 名称：该场景下的 tag_definition.name
        "activity_gate_tag_name": "activity_high",
    },

    # ========================================
    # 数据配置
    # ========================================
    "data": {
        "base_required_data": {
            "params": {
                "term": "daily",
                "tag_storage_entity_type": "stock_kline_daily",
            },
        },
        "extra_required_data_sources": [
            {"data_id": DataKey.TAG.value, "params": {"tag_scenario": "activity-ratio20"}},
        ],
        "min_required_records": 30,
        "indicators": {
            "rsi": [{"period": 14}],
        },
    },

    # 目标 / 风控配置：保持与 example 一致
    "goal": {
        "expiration": {"fixed_window_in_days": 30, "is_trading_days": True},
        "stop_loss": {"stages": [{"name": "loss10%", "ratio": -0.1, "close_invest": True}]},
        "take_profit": {
            "stages": [
                {"name": "win10%", "ratio": 0.1, "sell_ratio": 0.5},
                {"name": "win20%", "ratio": 0.2, "close_invest": True},
            ]
        },
    },

    # 股票采样配置：保持与 example 一致
    "sampling": {
        "strategy": "continuous",
        "sampling_amount": 2,
    },

    # 枚举器配置：保持与 example 一致（裁剪版）
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

    "fees": {
        "commission_rate": 0.00025,
        "min_commission": 5.0,
        "stamp_duty_rate": 0.001,
        "transfer_fee_rate": 0.0,
    },

    "price_simulator": {
        "use_sampling": False,
        "max_workers": "auto",
        "base_version": "latest",
    },

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
        "output": {"save_trades": True, "save_equity_curve": True},
    },

    "scanner": {"max_workers": "auto", "adapters": ["console"]},
}

