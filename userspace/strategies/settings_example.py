from core.modules.data_contract.contract_const import DataKey

# settings_example.py（完整选项说明版）
# ---------------------------------------------------------------------------
# 这个示例包含“当前系统可用的主要配置项”，并尽量给出：
# - 字段作用
# - 可选值
# - 默认行为（不写时系统怎么处理）
# ---------------------------------------------------------------------------
#
# 快速上手（最小可用）：
# - 必填建议：name / core / data.base_required_data / goal
# - 其他大多数字段可省略，系统会走默认值。
#
# 注意：
# - 这是“说明型模板”，不是推荐你把所有字段都写在真实策略里。
# - 真实策略建议保持简洁，只保留你真正要改的参数。

settings = {
    # =======================================================================
    # 1) 基础信息
    # =======================================================================
    # 策略唯一名称（用于目录、日志、版本记录）
    "name": "my_strategy",
    # 描述信息（仅用于说明）
    "description": "My first strategy",
    # 是否启用（scan/simulate 默认会跳过 is_enabled=False 的策略）
    "is_enabled": True,

    # =======================================================================
    # 2) 策略核心参数（你的策略私有参数）
    # =======================================================================
    "core": {
        # 示例参数：RSI 超卖阈值
        "rsi_oversold_threshold": 20,
        # 可自由扩展，名字随便取，是您自定义策略里的配置参数，例如：
        # "momentum_threshold": 0.05,
        # "volume_multiplier": 1.5,
    },

    # =======================================================================
    # 3) 数据配置（核心）
    # =======================================================================
    "data": {
        # 主数据依赖（必填）：DataKey 字符串 + 静态 params（与 data_contract 一致）
        # 主数据：仅 stock.kline；data_id 可省略；params.term 必填；adjust 默认 qfq
        "base_required_data": {
            "params": {"term": "daily"},
        },
        # 显式写 data_id 时只能为：
        # "base_required_data": {
        #     "data_id": DataKey.STOCK_KLINE.value,
        #     "params": {"term": "daily", "adjust": "qfq"},
        # },
        # 除主依赖外的其它数据（可省略；默认 []）
        "extra_required_data_sources": [
            {"data_id": DataKey.MACRO_GDP.value, "params": {}},
            # {"data_id": DataKey.TAG.value, "params": {"tag_scenario": "my-scenario"}},
            # {"data_id": DataKey.STOCK_CORPORATE_FINANCE.value, "params": {}},
        ],

        # 最少历史记录条数（可省略；默认为 100）
        # 具体意义是当前股票的记录至少要达到这个数值才会对当前股票进行策略计算。
        "min_required_records": 100,

        # 技术指标配置（可省略；默认 {}）
        # 只写你需要的指标，避免额外计算
        "indicators": {
            # ma: 移动平均
            "ma": [{"period": 5}, {"period": 20}],
            # ema: 指数移动平均
            # "ema": [{"period": 12}, {"period": 26}],
            # rsi: 相对强弱指标
            # "rsi": [{"period": 14}],
            # macd: 需 fast/slow/signal
            # "macd": [{"fast": 12, "slow": 26, "signal": 9}],
            # bbands: 布林带
            # "bbands": [{"period": 20, "std": 2.0}],
            # atr: 平均真实波动
            # "atr": [{"period": 14}],
        },
    },

    # =======================================================================
    # 4) 采样配置（供小规模测试策略使用 模式枚举/模拟使用）
    # =======================================================================
    "sampling": {
        # 采样策略（可省略；默认通常为 continuous）
        # 可选：uniform / stratified / random / continuous / pool / blacklist
        # 注意：以下所有可选参数里只能保留一种取样方式，不能同时使用多种取样方式。
        "strategy": "continuous",

        # 采样股票数量（可省略；默认通常为 10）
        "sampling_amount": 50,

        "continuous": {
            # 连续采样起始索引（可省略；默认 0）
            "start_idx": 0,
        },

        # 每种采样策略的子配置（按 strategy 选择性填写）
        # "uniform": {
        #     # 均匀采样一般不需要额外参数
        # },
        # "stratified": {
        #     # 分层采样随机种子（可省略）
        #     "seed": 42,
        # },
        # "random": {
        #     # 随机采样随机种子（可省略）
        #     "seed": 42,
        # },
        # "pool": {
        #     # 股票池采样：优先使用 stock_ids（inline）
        #     "stock_ids": ["000001.SZ", "000002.SZ"],
        #     # 如果 stock_ids 为空，可使用 file（相对当前策略目录）
        #     # 例如 userspace/strategies/<strategy_name>/stock_lists/test_stocks.txt
        #     # "file": "stock_lists/test_stocks.txt",
        # },
        # "blacklist": {
        #     # 黑名单采样：优先使用 stock_ids（inline）
        #     "stock_ids": ["000001.SZ"],
        #     # 如果 stock_ids 为空，可使用 file（相对当前策略目录）
        #     # "file": "stock_lists/blacklist.txt",
        # },
    },

    # =======================================================================
    # 5) 目标配置（止盈止损，建议保留）
    # =======================================================================
    "goal": {
        # 到期平仓（可选）
        # 如果不配置会一致模拟到股票完成所有止损或止盈目标为止。
        "expiration": {
            # 持仓窗口天数（推荐字段名）
            "fixed_window_in_days": 30,
            # True=按交易日计数，False=按自然日计数
            "is_trading_days": True,
        },

        # 分段止损（可选）
        "stop_loss": {
            # 注意如果是多个阶段，请确保至少有一个close_invest=True，或者所有止损目标的sell_ratio的和为1。
            "stages": [
                {
                    # 阶段名称（用于日志）
                    "name": "loss10%",
                    # 触发阈值：负数表示亏损比例
                    "ratio": -0.1,
                    # 触发后清仓（true 时可不写 sell_ratio）
                    "close_invest": True,
                    # 如果不清仓可写 sell_ratio（0~1）
                    # "sell_ratio": 0.5,
                }
            ]
        },

        # 分段止盈（可选）
        "take_profit": {
            # 注意如果是多个阶段，请确保至少有一个close_invest=True，或者所有止盈目标的sell_ratio的和为1。
            "stages": [
                {
                    "name": "win10%",
                    # 触发阈值：正数表示盈利比例
                    "ratio": 0.1,
                    # 部分卖出比例（0~1）
                    # 0.5代表卖出投资总股数的50%
                    "sell_ratio": 0.5,
                    # 追加动作（可选）：
                    # - set_protect_loss: 启用保本线 - 如果价格跌回到本金，按照protect_loss的配置操作
                    # - set_dynamic_loss: 启用动态止损 - 如果价格跌回到最高点回撤 N%，按照dynamic_loss的配置操作
                    "actions": ["set_protect_loss"],
                },
                {
                    "name": "win20%",
                    "ratio": 0.2,
                    # close_invest=True 表示直接清仓
                    "close_invest": True,
                    "actions": ["set_dynamic_loss"],
                },

            ]
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
    },

    # =======================================================================
    # 6) 枚举器配置（大多可省略）
    # =======================================================================
    "enumerator": {
        # 是否使用 sampling
        # False=全量输出到 output/；True=采样输出到 test/
        # 默认：False
        # "use_sampling": False,

        # 最多保留 test 版本数（默认：10）
        # "max_test_versions": 10,

        # 最多保留 output 版本数（默认：3）
        # "max_output_versions": 3,

        # 并发 worker（"auto" 或整数，默认 "auto"）
        # "max_workers": "auto",

        # 是否输出更详细调度日志（默认：False）
        # "is_verbose": False,

        # Memory-aware scheduler 参数（可全省略，默认 auto/5）
        # "memory_budget_mb": "auto",
        # "warmup_batch_size": "auto",
        # "min_batch_size": "auto",
        # "max_batch_size": "auto",
        # "monitor_interval": 5,
    },

    # =======================================================================
    # 7) 公共交易费率（可省略）
    # =======================================================================
    # 说明：
    # - price_simulator.fees / capital_simulator.fees 可覆盖这里
    "fees": {
        "commission_rate": 0.00025,  # 佣金率
        "min_commission": 5.0,       # 最低佣金
        "stamp_duty_rate": 0.001,    # 印花税（卖出）
        "transfer_fee_rate": 0.0,    # 过户费
    },

    # =======================================================================
    # 8) 价格因子模拟器配置（大多可省略）
    # =======================================================================
    "price_simulator": {
        # 版本来源选择：
        # True=读 test/*，False=读 output/*（默认 True）
        # "use_sampling": False,

        # 基础版本号（默认 latest）
        # 支持："latest" / "1" / "2" ...
        # 如果use_sampling=True，则读取result/test/目录下的版本；如果use_sampling=False，则读取result/output/目录下的版本。
        # "base_version": "latest",

        # 并发 worker（默认 auto）
        # "max_workers": "auto",

        # 时间窗口（可省略；空=使用枚举输出结果全量时间）
        # "start_date": "20230101",
        # "end_date": "20241231",

        # 模拟器专属费用覆盖（可选）
        # "fees": {
        #     "commission_rate": 0.0002,
        #     "min_commission": 5.0,
        #     "stamp_duty_rate": 0.001,
        #     "transfer_fee_rate": 0.0,
        # },
    },

    # =======================================================================
    # 9) 资金分配模拟器配置（大多可省略）
    # =======================================================================
    "capital_simulator": {
        # 版本来源选择（默认 True）
        # "use_sampling": False,

        # 版本号（默认 latest）
        # 如果use_sampling=True，则读取result/test/目录下的版本；如果use_sampling=False，则读取result/output/目录下的版本。
        # "base_version": "latest",

        # 初始资金（默认 1_000_000）
        "initial_capital": 1_000_000,

        # 时间窗口（可选；不写则继承 price_simulator 或使用全量）
        # "start_date": "20230101",
        # "end_date": "20241231",

        # 资金分配参数（均可省略，有默认）
        "allocation": {
            # 可选：equal_capital / equal_shares / kelly / custom
            "mode": "equal_capital",
            # 最大持仓数
            "max_portfolio_size": 10,
            # 单票最大权重（0~1）
            "max_weight_per_stock": 0.3,
            # equal_shares 模式参数
            "lot_size": 100,
            "lots_per_trade": 1,
            # kelly 模式参数
            "kelly_fraction": 0.5,
        },

        # 覆盖公共费用（可选）
        # "fees": {
        #     "commission_rate": 0.00025,
        #     "min_commission": 5.0,
        #     "stamp_duty_rate": 0.001,
        #     "transfer_fee_rate": 0.0,
        # },

        # 输出开关（默认均 True）
        "output": {
            # 是否保存逐笔交易日志
            "save_trades": True,
            # 是否保存每日权益曲线
            "save_equity_curve": True,
        },
    },

    # =======================================================================
    # 10) 扫描器配置（可省略）
    # =======================================================================
    "scanner": {
        # 并发 worker（默认 auto）
        "max_workers": "auto",

        # 输出适配器列表（默认 ["console"]）
        # 表示如何继续处理用当前策略扫描出的投资机会 - 可以某种方式通知，可以使用第三方服务自动下单，可以进行机器学习等等。
        # 取决于您在 adapter 里扩展了什么，系统默认只自带 console（命令行输出）。其他适配方式需自行扩展
        # 示例（只是举例，没有实现）：["console"], ["console", "sms", "machine_learning"], ["wechat", "email"]
        "adapters": ["console"],

        # 是否严格按“上一个交易日”进行扫描（默认 True）
        # 如果True，比如今天是2025-12-10日，如果发现数据库最新的一个K线记录只到2025年6月30日，则扫描器会拒绝扫描。
        # 如果False，比如今天是2025-12-10日，如果发现数据库最新的一个K线记录只到2025年6月30日，则扫描器会扫描2025年6月30日当天的策略产生的机会。
        "use_strict_previous_trading_day": True,
        
        # 扫描缓存天数（默认 10）
        # 保留最近 N 个扫描日期目录，多于这个数量的结果会被自动删除。
        "max_cache_days": 10,

        # 股票列表文件路径，可以是相对路径，也可以是绝对路径。
        "watch_list": "path/to/watch_list.txt", 
    },
}
