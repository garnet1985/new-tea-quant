# 用户策略目录

这里存放所有用户自定义的策略。

## 目录结构

```
app/userspace/strategies/
├── example/                     # 示例策略
│   ├── strategy_worker.py       # Worker 实现
│   ├── settings.py              # 配置文件
│   └── results/                 # 结果存储（自动生成）
│       ├── scan/                # 扫描结果
│       └── simulate/            # 模拟结果
│
├── momentum/                    # 动量策略
├── mean_reversion/              # 均值回归策略
└── ...
```

## 创建新策略

1. 创建策略文件夹（如 `my_strategy/`）
2. 创建 `strategy_worker.py`，继承 `BaseStrategyWorker`
3. 创建 `settings.py`，定义策略配置
4. 实现 `scan_opportunity()` 和 `simulate_opportunity()` 方法

## 示例

参考 `example/` 文件夹中的示例代码。
