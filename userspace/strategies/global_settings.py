"""
全局配置

说明：
- 只包含跨策略的系统级配置
- 大部分配置（sampling、data、performance）应该在各策略的 settings.py 里
- 策略可以覆盖这些全局配置
"""

# ========================================
# CapitalAllocationSimulator 默认配置
# ========================================
DEFAULT_ALLOCATION = {
    # 资金配置
    "capital": {
        "initial_capital": 100000,           # 初始资金（元）
        "fixed_amount_per_trade": 5000       # 每笔固定金额（元，MVP）
        
        # 未来：凯莉公式
        # "allocation_method": "kelly",      # fixed / kelly
        # "kelly_divisor": 4,                # 凯莉除数（风险控制）
    },
    
    # 交易费用
    "fees": {
        "buy_fee_rate": 0.0003,              # 买入费率（万 3）
        "sell_fee_rate": 0.0013              # 卖出费率 + 印花税（万 3 + 千 1）
    },
    
    # 执行配置
    "execution": {
        "order": "sell_first"                # 买卖顺序：sell_first / buy_first
    },
    
    # OpportunityEnumerator 预处理配置
    "preprocess": {
        "mode": "simplified",                # simplified / full
        "signal_window": 3,                  # 信号有效期（天）
        "use_cache": True,                   # 使用缓存
        "parallel": True,                    # 多进程并行
        "max_workers": 10                    # 最大并行数
    }
}


# ========================================
# OpportunityEnumerator 配置
# ========================================
# 注意：OpportunityEnumerator 没有全局配置
# max_workers 在调用时指定
# 不使用缓存（每次重新计算）


# ========================================
# 未来：多个 Allocation 配置（V2，roadmap）
# ========================================
# ALLOCATION_CONFIGS = {
#     # 保守配置
#     "conservative": {
#         "capital": {
#             "initial_capital": 100000,
#             "fixed_amount_per_trade": 3000  # 每笔少
#         },
#         "fees": {...},
#         ...
#     },
#     
#     # 激进配置
#     "aggressive": {
#         "capital": {
#             "initial_capital": 100000,
#             "fixed_amount_per_trade": 10000  # 每笔多
#         },
#         "fees": {...},
#         ...
#     },
#     
#     # 凯莉公式配置
#     "kelly": {
#         "capital": {
#             "initial_capital": 100000,
#             "allocation_method": "kelly",
#             "kelly_divisor": 4
#         },
#         "fees": {...},
#         ...
#     }
# }
