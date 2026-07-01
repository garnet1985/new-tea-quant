settings = {
    # 系统 discovery 暂用路径 key；CLI 未来将使用 meta.key
    # ========================================
    "is_enabled": True,
    "meta": {
        "key": "stock_based_rsi",
        "display_name": "RSI超跌反弹 + 财报正常",
        "description": (
            "演示策略：RSI(14) 超卖触发买入，并要求最新已披露季度净利润同比不低于阈值。"
            "演示意义：技术信号负责「何时看」，基本面负责「能不能买」——避免在盈利恶化的下跌里接飞刀。"
        ),
        "keywords": ["性能测试"],
        "details": {
            "entry": [
                "RSI(14) 低于超卖阈值（见 core.rsi_oversold_threshold，默认 20）",
                "最新已披露季度 netprofit_yoy ≥ core.min_netprofit_yoy（默认 0，即不同比下滑）",
                "财报 PIT 由 stock.finance.quarterly 的 ann_date 时间轴 + DataCursor 切片保证",
            ],
        },
    },
    "market_profile": "china_a_stock",

    # ========================================
    # 策略核心参数
    # ========================================
    "core": {
        "rsi_oversold_threshold": 20,
        "min_netprofit_yoy": 0.0,
        "start_date": "20240101",
        "end_date": "20241231",
    },

    # ========================================
    # 数据配置
    # ========================================
    "data": {
        "base": {
            "data_key": "stock.kline.daily",
            "params": {"adjust": "qfq"},
            "indicators": {
                "rsi": [{"length": 14}],
            },
        },
        "required": [
            {"data_key": "stock.finance.quarterly", "params": {}},
        ],
        "min_required_records": 30,
    },

    # 与 random_v1 对齐：收盘出信号 → 次日开盘成交；对称 ±20% goal
    "simulation": {
        "template": "custom",
        "execution_mode": "entity_based",
        "monitor_price_model": "close",
        "buy_price_model": "next_open",
        "sell_price_model": "close",
        "slippage": {"buy_bps": 5.0, "sell_bps": 5.0},
        "edges": {
            "no_next_bar": "skip_trade",
            "allow_buy_at_limit_up": False,
            "allow_sell_at_limit_down": False,
        },
        "retention": {
            "max_output_versions": 5,
        },
    },

    "goal": {
        "stop_loss": {
            "stages": [
                {"name": "loss20%", "ratio": -0.2, "close_invest": True},
            ],
        },
        "take_profit": {
            "stages": [
                {"name": "win20%", "ratio": 0.2, "close_invest": True},
            ],
        },
    },

    "sampling": {
        "use_sampling": True,
        "strategy": "uniform",
        "sampling_amount": 500,
        "stock_pool": ["600000.SH"],
    },

    "enumerator": {
        "is_verbose": False,
    },

    "fees": {
        "commission_rate": 0.00025,
        "min_commission": 5.0,
        "stamp_duty_rate": 0.001,
        "transfer_fee_rate": 0.0,
    },

    "price_simulator": {
        "base_version": "latest",
    },

    "capital_simulator": {
        "base_version": "latest",
        "initial_capital": 100_000,
        "allocation": {
            "mode": "equal_capital",
            "max_portfolio_size": 10,
            "max_weight_per_stock": 0.3,
            "lots_per_trade": 1,
            "kelly_fraction": 0.5,
            "skip_trade_when_insufficient": True,
        },
        "output": {
            "save_trades": True,
            "save_equity_curve": True,
        },
    },

    "scanner": {
        "adapters": ["console"],
        "use_strict_previous_trading_day": False,
        "max_cache_days": 10,
        "watch_list": "",
    },
}
