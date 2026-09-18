---
title: manage version 策略版本管理
aliases:
  - version
  - pin
  - unpin
  - delete
  - cache
summary: 使用NTQ为一个实体贴上不同的标签。
---

# 如何管理版本

## 基本概念

每次完整回测产生一个版本（version），版本绑定指纹用于缓存判断。详见 [版本与指纹系统](../wiki/strategy/effective_settings_fingerprint.md)。

## CLI 命令

| 命令                                      | 缩写    | 说明     |
| --------------------------------------- | ----- | ------ |
| `python cli.py strategy_delete_version` | `sdv` | 删除一个版本 |
| `python cli.py strategy_pin_version`    | `spn` | 固定一个版本 |
| `python cli.py strategy_unpin_version`  | `sup` | 取消固定   |

所有命令都需要 `--strategy` 参数，格式为 `策略key:版本号`。

## 删除版本

```bash
python cli.py sdv --strategy demo/random/random_v1:3
```

- 删除该版本的 `enum/`、`price/`、`portfolio/`、`analysis/` 目录

- 从 `meta.json` 的 registry 中移除

- `settings.py` 不受影响

- 如果该版本被 pin 了，需要先 unpin

## 固定版本

```bash
python cli.py spn --strategy demo/random/random_v1:3
```

- 固定后不被自动清理

- 只改 `meta.json` 的 `pinned` 列表

- 不改 settings、不绑定 Run

## 取消固定

```bash
python cli.py sup --strategy demo/random/random_v1:3
```

取消固定后，该版本可能被 Keep-N 清理。

## 版本号格式

`--strategy` 参数的版本号部分支持两种写法：

```bash
python cli.py sdv --strategy my_strategy:3      # 数字
python cli.py sdv --strategy my_strategy:v3     # 带 v 前缀
```

## Keep-N 自动清理

版本数量有上限（`data.json` → `retention.simulation_results_max_versions`）。

- 触顶时**拒绝分配新版本**，不静默删除

- 清理时删未 pin 且号更靠前的版本

- pin 的版本不会被清理

## 什么时候会换版本

| 条件                    | 行为                |
| --------------------- | ----------------- |
| settings 白名单字段变了      | 新版本               |
| 股票池变了                 | 新版本               |
| NTQ 升级 / hooks 源码改了   | 旧版本变 env\_invalid |
| 只改 meta / is\_enabled | 不换版本              |

## env\_invalid 状态

环境变了（NTQ 升级、hooks 改了）后，旧版本进入 `env_invalid`：

- 报告仍可打开、对比

- 配置可恢复到 settings.py

- **不能继续跑**（不能补步、不能 cache hit）

- UI 显示"环境已更新 / 仅供查阅"

## 恢复旧版本配置

恢复版本只把 `settings.json` 写回 `settings.py`，**不**恢复历史股票池。下次 Run 用今天的股票池算指纹，如果池子不同会开新版本。

## 常见操作

| 场景     | 命令                                        |
| ------ | ----------------------------------------- |
| 固定重要版本 | `python cli.py spn --strategy my_strat:1` |
| 删除错误版本 | `python cli.py sdv --strategy my_strat:3` |
| 取消固定   | `python cli.py sup --strategy my_strat:1` |
| 查看版本信息 | `python cli.py v`                         |

