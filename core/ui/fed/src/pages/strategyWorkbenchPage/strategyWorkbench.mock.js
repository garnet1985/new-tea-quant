export const defaultMetaInfo = {
  name: 'example',
  is_enabled: true,
  description: 'Example RSI oversold strategy (minimal settings)',
};

export const defaultSettings = {
  // core 按 userspace/strategies/example/settings.py
  core: {
    rsi_oversold_threshold: 20,
  },
  // 其余字段尽量贴近 settings_example 的完整结构
  data: {
    base_required_data: {
      params: { term: 'daily' },
    },
    extra_required_data_sources: [],
    min_required_records: 30,
    indicators: {
      rsi: [{ period: 14 }],
    },
  },
  goal: {
    expiration: {
      fixed_window_in_days: 30,
      is_trading_days: true,
    },
    stop_loss: {
      stages: [{ name: 'loss10%', ratio: -0.1, close_invest: true }],
    },
    take_profit: {
      stages: [
        { name: 'win10%', ratio: 0.1, sell_ratio: 0.5 },
        { name: 'win20%', ratio: 0.2, close_invest: true },
      ],
    },
  },
  sampling: {
    strategy: 'continuous',
    sampling_amount: 2,
  },
  enumerator: {
    use_sampling: false,
    max_test_versions: 3,
    max_output_versions: 2,
    max_workers: 'auto',
    is_verbose: true,
    memory_budget_mb: 'auto',
    warmup_batch_size: 'auto',
    min_batch_size: 'auto',
    max_batch_size: 'auto',
    monitor_interval: 5,
  },
  fees: {
    commission_rate: 0.00025,
    min_commission: 5.0,
    stamp_duty_rate: 0.001,
    transfer_fee_rate: 0.0,
  },
  price_simulator: {
    use_sampling: false,
    // 兼容 settings_example 的完整块：时间窗口可为空，表示走全量输出时段
    start_date: '',
    end_date: '',
    max_workers: 'auto',
    base_version: 'latest',
    fees: {
      commission_rate: 0.00025,
      min_commission: 5.0,
      stamp_duty_rate: 0.001,
      transfer_fee_rate: 0.0,
    },
  },
  capital_simulator: {
    use_sampling: false,
    base_version: 'latest',
    initial_capital: 1000000,
    start_date: '',
    end_date: '',
    max_workers: 'auto',
    allocation: {
      mode: 'equal_capital',
      max_portfolio_size: 10,
      max_weight_per_stock: 0.3,
      lot_size: 100,
      lots_per_trade: 1,
      kelly_fraction: 0.5,
    },
    output: {
      save_trades: true,
      save_equity_curve: true,
    },
    fees: {
      commission_rate: 0.00025,
      min_commission: 5.0,
      stamp_duty_rate: 0.001,
      transfer_fee_rate: 0.0,
    },
  },
  scanner: {
    max_workers: 'auto',
    adapters: ['console'],
  },
};
