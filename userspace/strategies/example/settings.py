from core.global_enums.enums import EntityType, AdjustType

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
        # 基础价格数据源（K 线类型）
        "base_price_source": EntityType.STOCK_KLINE_DAILY.value,
        # 复权方式
        "adjust_type": AdjustType.QFQ.value,
        
        # 最小要求的基础周期记录数
        "min_required_records": 200,

        # 仅计算本策略需要的 RSI 指标
        "indicators": {
            "rsi": [
                {"period": 14}
            ]
        },

        # 额外数据源（GDP、tag、corporate_finance 等）
        "extra_data_sources": []
    },

    "goal": {
        # 简单的到期平仓
        "expiration": {
            "fixed_window_in_days": 30,
            "is_trading_days": True
        },
        # 简单的止损
        "stop_loss": {
            "stages": [
                {
                    "name": "loss10%",
                    "ratio": -0.1,
                    "close_invest": True
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
                    "close_invest": True
                }
            ]
        }
    },

    # ========================================
    # 股票采样配置（示例：固定池中采样少量股票）
    # ========================================
    "sampling": {
        "strategy": "continuous",
        "sampling_amount": 2,
        # "pool": {
        #     # 直接在配置中给出一个很小的股票池，方便快速测试
        #     "stock_pool": ["000001.SZ", "000002.SZ"],
        # }
    },

    # ========================================
    # 枚举器配置
    # ========================================
    "enumerator": {
        # 是否使用采样配置 - 如果您要全量枚举，请切记关闭此选项（False）
        # True: 使用 sampling 配置进行采样枚举（结果保存在 test/ 子目录）
        # False: 使用全量股票列表进行枚举（结果保存在 output/ 子目录，作为 SOT）
        "use_sampling": False,
        
        # 最多保留的测试模式版本数（默认 10）
        # 超过此数量的测试版本会被自动清理（删除最早的版本）
        "max_test_versions": 3,
        
        # 最多保留的全量枚举（output）版本数（默认 3）
        # 超过此数量的全量版本会被自动清理（删除最早的版本）
        "max_output_versions": 2,

        # 枚举器专用 worker 数量（"auto" 或具体数字）
        "max_workers": "auto",

        # 是否输出详细 worker/scheduler 决策日志
        "is_verbose": True,
        
        # Memory-aware batch scheduler 配置（全部支持 "auto" 自动计算）
        # 内存预算（MB），"auto" 表示自动计算（系统可用内存的 70%）
        "memory_budget_mb": "auto",
        # 初始批次大小，"auto" 表示根据任务总数自动计算
        "warmup_batch_size": "auto",
        # 最小/最大批次大小，"auto" 表示根据任务总数自动计算
        "min_batch_size": "auto",
        "max_batch_size": "auto",
        # 每多少个 batch 输出一次监控日志
        "monitor_interval": 5,
    },

    # ========================================
    # 交易成本配置（公用配置，可被 price_simulator / capital_simulator 覆盖）
    # ========================================
    "fees": {
        "commission_rate": 0.00025,      # 佣金率（双边，万2.5）
        "min_commission": 5.0,            # 最低佣金（元）
        "stamp_duty_rate": 0.001,         # 印花税率（卖出时，千1）
        "transfer_fee_rate": 0.0,         # 过户费（如需要）
    },

    # ========================================
    # 模拟器配置
    # ========================================
    "price_simulator": {
        # 是否使用采样配置 - 如果您要全量枚举，请切记关闭此选项（False）
        "use_sampling": False,

        # 模拟器专用 worker 数量（"auto" 或具体数字）
        "max_workers": "auto",

        "base_version": "latest",

        # 时间窗口（可选），为空表示使用 SOT 全量时间
        # "start_date": "",
        # "end_date": "",

        # 枚举版本依赖（读取 test 还是 output 由 use_sampling 决定）
        #   - "latest": 使用对应目录的最新版本
        #   - "1": 使用对应目录的指定版本号
        #   - 如果没配置 / 配置找不到：回退到对应目录 latest
        #   - 如果对应目录没有任何版本：会先自动触发一次对应模式枚举
        # "base_version": "latest",
    },

    # ========================================
    # 资金分配模拟器配置（CapitalAllocationSimulator）
    # ========================================
    "capital_simulator": {
        # 是否使用采样配置 - 如果您要全量枚举，请切记关闭此选项（False）
        "use_sampling": False,

        # 枚举版本依赖（与 PriceFactor 一样的语义）
        "base_version": "latest",

        # 初始资金（元）
        "initial_capital": 1_000_000,

        # 资金分配策略
        "allocation": {
            # 分配模式：
            #   - "equal_capital": 每个机会等额资金（按 initial_capital / max_portfolio_size 分配）
            #   - "equal_shares": 每个机会固定股数（按 lot_size * lots_per_trade 计算）
            #   - "kelly": 使用 Kelly 公式计算仓位
            "mode": "equal_capital",

            # 最大组合持仓数（同时最多持有多少只股票）
            "max_portfolio_size": 10,

            # 单只股票最大权重（0~1，防止过度集中）
            # 例如：总资产100万，某只股票最多占30万（30%），超过时需要减仓
            "max_weight_per_stock": 0.3,

            # equal_shares 模式下的配置
            "lot_size": 100,              # 1手对应的股票数（A股通常是100股）
            "lots_per_trade": 1,          # 每次买入的手数（例如：1手、2手等）

            # kelly 模式下的配置
            "kelly_fraction": 0.5,        # Kelly 仓位的折扣比例（0~1，用于风险控制）
        },

        # 输出控制（可选）
        "output": {
            # 是否保存逐笔交易日志
            "save_trades": True,
            # 是否保存每日权益曲线
            "save_equity_curve": True,
        },
    },

    "scanner": {
        "max_workers": "auto",
        "adapter_name": "console"
    },
}
