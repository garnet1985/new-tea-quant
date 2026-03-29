# 策略目录（`userspace/strategies/`）

每个子目录 = 一个策略，**目录名**一般与 `settings.py` 里的 `"name"` 一致。

## 每个策略最少包含

| 文件 | 作用 |
|------|------|
| `settings.py` | 策略配置：`data`、`goal`、`enumerator`、`price_simulator`、`capital_simulator`、`sampling` 等 |
| `strategy_worker.py` | 继承 `BaseStrategyWorker`，实现 `scan_opportunity()`（必选）等 |

可选：`stock_lists/` 下放文本股票池，在 `sampling.pool.file` / `sampling.blacklist.file` 中引用（相对本策略目录）。

## 新建策略

1. 复制 `example/` 或对照 [settings_example.py](settings_example.py) 写 `settings.py`。  
2. 实现 `strategy_worker.py`。  
3. 将 `"is_enabled": True` 设为要跑的策略；同时只启用一个可避免 CLI 歧义。  

更细的写法见 [策略开发指南](../../docs/user-guide/strategy-development.md)。

## 回测结果（本地）

运行枚举/模拟后，结果通常在：

`userspace/strategies/<策略名>/results/`  

该目录默认被 `.gitignore`，勿把大结果提交进 Git。

## 示例策略

- **example**：RSI 示例，配置最完整。  
- **random / momentum**：演示用策略，可按需启用。
