settings = {
    "is_enabled": True,
    # 系统 discovery 暂用路径；CLI 未来将使用 meta.key
    "meta": {
        "key": "slice_low_price_v2",
        "display_name": "低价股 · v2 年度换仓（PIT · 仅价格）",
        "description": (
            "与 v1 逻辑相同，但股票池为 PIT：含回测期内中途退市股票。"
            "用于对比幸存者偏差（v1）与真实可参与集合（v2）。"
        ),
        "keywords": ["演示", "低价股", "PIT", "slice_based"],
        "details": {
            "entry": [
                "股票池真正的所有股票（包含模拟过程中可能退市的股票）",
                "筛选出1-5元之间的股票，每年选出20只最低价的股票，持有约一年",
                "每年换仓一次",
            ],
        },
    },
    "market_profile": "china_a_stock",
    "core": {
        "universe_mode": "pit",
        "rebalance_period": "year",
        "min_close": 1.0,
        "max_close": 5.0,
        "top_n": 20,
        "cap_filter": "none",
    },
    "data": {
        "base": {
            "data_key": "stock.kline.daily",
            "params": {"adjust": "qfq"},
            "indicators": {},
        },
        "required": [],
        "min_required_records": 1,
    },
    "simulation": {
        "start_date": "20240101",
        "end_date": "20241231",
        "template": "custom",
        "execution_mode": "slice_based",
        "monitor_price_model": "close",
        "buy_price_model": "close",
        "sell_price_model": "close",
        "slippage": {"buy_bps": 5.0, "sell_bps": 5.0},
        "edges": {
            "no_next_bar": "skip_trade",
            "allow_buy_at_limit_up": False,
            "allow_sell_at_limit_down": False,
        },
        "retention": {"max_output_versions": 5},
        "execute_steps": [
            "check_settlement",
            "check_stop_loss",
            "check_take_profit",
            "check_expiration",
        ],
    },
    "goal": {"is_customized": True},
    "sampling": {
        "use_sampling": True,
        "strategy": "pool",
        "sampling_amount": 500,
        "pool": {"stock_ids": ["600000.SH", "600036.SH"]},
    },
    "enumerator": {"is_verbose": False},
    "fees": {
        "commission_rate": 0.00025,
        "min_commission": 5.0,
        "stamp_duty_rate": 0.001,
        "transfer_fee_rate": 0.0,
    },

    "portfolio": {
        "base_version": "latest",
        "initial_capital": 25_000,
        "allocation": {
            "mode": "equal_shares",
            "max_portfolio_size": 20,
            "lots_per_trade": 2,
            "skip_trade_when_insufficient": True,
        },
        "output": {"save_trades": True, "save_equity_curve": True},
    },
    "scanner": {
        "adapters": ["console"],
        "use_strict_previous_trading_day": False,
        "max_cache_days": 10,
        "watch_list": "",
    },
}
