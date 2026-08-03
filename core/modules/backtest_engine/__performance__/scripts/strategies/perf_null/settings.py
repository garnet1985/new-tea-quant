# Minimal strategy for BE __performance__ (daily kline only; matches fake_data).
settings = {
    "is_enabled": True,
    "meta": {
        "key": "be_perf_null",
        "display_name": "BE perf null enumerate",
        "description": (
            "Null-hook enumerate against synthetic DuckDB "
            "(preload + as-of; mode set by test_script)."
        ),
        "keywords": ["be_perf"],
    },
    # core.rebalance_period used by slice_based executor (default year if absent).
    # entity_based ignores it.
    "market_profile": "china_a_stock",
    "core": {"rebalance_period": "year"},
    "data": {
        "base": {
            "data_key": "stock.kline.daily",
            "params": {"adjust": "none"},
            "indicators": {},
        },
        "required": [],
        "min_required_records": 5,
    },
    "simulation": {
        "retention": {"max_output_versions": 2},
        "execution": {
            "start_date": "20240101",
            "end_date": "20241231",
            "mode": "entity_based",
        },
        "assumption": {
            "template": "custom",
            "tradability": {
                "monitor_price": "close",
                "enter_price": "next_open",
                "exit_price": "close",
                "slippage": {"enter_bps": 0.0, "exit_bps": 0.0},
                "edges": {
                    "no_next_tick": "skip_trade",
                    "allow_enter_at_limit_up": False,
                    "allow_exit_at_limit_down": False,
                },
                "liquidity": {
                    "max_participation_rate": 1.0,
                    "participation_on_exceed": "clip",
                },
                "delisted_exit_price": "last_tradable_close",
            },
        },
        "risk_control": {"skip_enter_when": [], "force_exit_when": []},
    },
    "goal": {
        "expiration": {"fixed_window_in_days": 5, "mode": "open_day"},
        "stop_loss": {"stages": []},
        "take_profit": {"stages": []},
    },
    "sampling": {
        "use_sampling": True,
        "strategy": "pool",
        "sampling_amount": 10,
        "pool": {"stock_ids": []},
    },
    "enumerator": {"is_verbose": False},
    "fees": {
        "commission_rate": 0.0,
        "min_commission": 0.0,
        "stamp_duty_rate": 0.0,
        "transfer_fee_rate": 0.0,
    },
    "portfolio": {
        "base_version": "latest",
        "initial_capital": 100000,
        "allocation": {
            "mode": "equal_capital",
            "max_portfolio_size": 10,
            "max_weight_per_stock": 1.0,
            "lots_per_trade": 1,
            "kelly_fraction": 0.5,
            "skip_trade_when_insufficient": True,
        },
        "output": {"save_trades": False, "save_equity_curve": False},
    },
    "scanner": {
        "adapters": ["console"],
        "use_strict_previous_trading_day": False,
        "max_cache_days": 10,
        "watch_list": "",
    },
}
