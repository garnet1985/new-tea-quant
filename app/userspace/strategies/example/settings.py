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
        "sampling_amount": 20,
        # "pool": {
        #     # 直接在配置中给出一个很小的股票池，方便快速测试
        #     "stock_pool": ["000001.SZ", "000002.SZ"],
        # }
    },

    # ========================================
    # 枚举器配置
    # ========================================
    "enumerator": {
        # 是否使用采样配置（默认 True）
        # True: 使用 sampling 配置进行采样枚举（结果保存在 test/ 文件夹）
        # False: 使用全量股票列表进行枚举（结果保存在 sot/ 文件夹）
        "use_sampling": True,
        
        # 最多保留的测试模式版本数（默认 10）
        # 超过此数量的测试版本会被自动清理（删除最早的版本）
        "max_test_versions": 10,
        
        # 最多保留的全量枚举（SOT）版本数（默认 3）
        # 超过此数量的全量版本会被自动清理（删除最早的版本）
        "max_sot_versions": 3,

        # 枚举器专用 worker 数量（"auto" 或具体数字）
        "max_workers": "auto",
    },

    # ========================================
    # 模拟器配置
    # ========================================
    "simulator": {
        # 时间窗口（可选），为空表示使用 SOT 全量时间
        "start_date": "",
        "end_date": "",
        
        # 枚举版本依赖（"latest" 表示使用最新的 SOT 版本）
        # 支持格式：
        #   - "latest": 使用最新的 SOT 版本（sot/ 目录）
        #   - "test/latest": 使用最新的测试版本（test/ 目录）
        #   - "1_20260112_161317": 使用指定版本号
        "sot_version": "latest",
        
        # 是否使用采样配置（默认 True）
        "use_sampling": True,
        
        # 模拟器专用 worker 数量（"auto" 或具体数字）
        "max_workers": "auto",
    },
}
