---
title: manage version 策略版本管理
aliases:
  - version
  - delete
  - cache
  - 版本
  - 删除版本
summary: 删除策略回测版本。
---

# 如何管理版本

## 基本概念

每次完整回测产生一个版本（version），版本绑定指纹用于缓存判断。概念说明见 [生效设置与指纹系统](../wiki/effective_settings_fingerprint.md)。

## CLI 命令

| 命令                                      | 缩写    | 说明     |
| --------------------------------------- | ----- | ------ |
| `python cli.py strategy_delete_version` | `sdv` | 删除一个版本 |

所有命令都需要 `--strategy` 参数，格式为 `策略key:版本号`。

## 删除版本

```bash
python cli.py sdv --strategy random_v1:3
```

- 删除该版本的 `enum/`、`price/`、`portfolio/`、`analysis/` 目录

- 从 `meta.json` 的 registry 中移除

- `settings.py` 不受影响

## 版本号格式

`--strategy` 参数的版本号部分支持两种写法：

```bash
python cli.py sdv --strategy my_strategy:3      # 数字
python cli.py sdv --strategy my_strategy:v3     # 带 v 前缀
```

## 过时环境自动清理

过时 `env_fp` 最多留几组（`data.json` → `retention.simulation_results_max_stale_envs`，默认 5）。

- 当前环境整组保留，不按 version 号抽

- 超出则删最旧的那一组（含对应归因报告）

- 开新号不会因为份数触顶而拒绝

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

- 配置可在 **制定策略 UI** 里写回 `settings.py`（没有对应 CLI）

- **不能继续跑**（不能补步、不能 cache hit）

- 工作台会显示「环境已更新 / 仅供查阅」

## 恢复旧版本配置（UI）

在制定策略页把历史 version 的配置写回 `settings.py`。这只恢复当时的 settings，**不**恢复历史股票池。下次 Run 用今天的股票池算指纹，池子不同会开新版本。

## 常见操作

| 场景     | 命令                                        |
| ------ | ----------------------------------------- |
| 删除错误版本 | `python cli.py sdv --strategy my_strat:3` |
| 查看 NTQ 核心版本 | `python cli.py v`                         |

