---
title: 生效设置与指纹系统
aliases:
  - version
  - fingerprint
  - effective settings
  - cache
  - 版本
  - 指纹
  - 缓存
  - 生效设置
summary: 回测 version 如何用生效设置指纹命中缓存，以及何时仅供查阅。
---


# 版本与指纹系统

## 核心概念

每次完整回测产生一个版本（version）。版本绑定当时的指纹，用于判断"这次回测和之前某次是否完全一样"。

## 两种指纹

| 指纹           | 含义       | 内容                                           |
| ------------ | -------- | -------------------------------------------- |
| `execute_fp` | 可逆的执行输入  | 白名单 settings ⊕ 本次解析出的 entity\_ids（股票池）       |
| `env_fp`     | 不可逆的执行环境 | NTQ/core 版本、hooks 源码、DB 类型、data\_contract 映射 |

命中键 = `execute_fp + env_fp`。两个都一样 → 命中已有版本，直接返回缓存结果。

## 什么是 Effective Settings

settings.py 里的字段不是全部参与指纹。只有**白名单字段**（effective settings）才进指纹计算。

白名单外的字段（如 `meta`、`is_enabled`、`scanner`、`analysis`）不影响回测结果，改了不换版本。

白名单由框架维护（含 core / data / goal / simulation / portfolio 等块）。`meta`、`is_enabled`、`scanner`、`analysis` 不进指纹。

## 何时换版本

| 条件                             | 行为                              |
| ------------------------------ | ------------------------------- |
| execute\_fp + env\_fp 都已有      | 命中已有版本，秒返回                      |
| settings 白名单变了                 | execute\_fp 变 → 新版本             |
| 股票池变了（settings 没改）             | execute\_fp 变 → 新版本（但不算"设置已变更"） |
| env 变了，当前 env 下已有该 execute\_fp | 命中新 env 的版本                     |
| env 变了，当前 env 下没有该 execute\_fp | 新版本，旧版本变"仅供查阅"                  |
| 只改非 effective 字段               | 不换版本                            |
| 只切换选中版本，没跑                     | 只换报告，不产生新版本                     |

## env\_invalid 状态

当环境指纹变了（比如 NTQ 升级了版本，或者 hooks 源码改了），旧版本的 `env_fp` 和当前环境不一致，进入 `env_invalid` 状态：

- 版本报告仍然可以打开、对比

- 配置可以恢复到 settings.py

- 但**不能继续跑**（不能补步、不能 cache hit）

- UI 显示"环境已更新 / 仅供查阅"

## Pin / Unpin

- `pin`：固定版本，不被自动清理。只改 `meta.json` 的 `pinned` 列表

- `unpin`：取消固定

- pin 不改 settings、不绑定 Run、不禁止手动删除

## Keep-N

版本数量有上限（`data.json` → `retention.simulation_results_max_versions`）。触顶时**拒绝分配新版本**，不静默删除。删未 pin 且号更靠前的版本。

## 磁盘布局

```
{strategy}/results/simulations/
  meta.json                     # 索引：next_version_id + registry + pinned
  {vid}/
    settings.json               # 当时完整 settings（恢复用）
    effective_settings.json     # 白名单投影（不含 entity_ids）
    scope.json                  # { entity_ids, start_date, end_date }
    enum/ | price/ | portfolio/  # 三步产物
    runtime_env.json            # 该步完成标记
    analysis/                   # 归因产物
```

## 恢复 vs 股票池

恢复版本只把 `settings.json` 写回 `settings.py`，**不**把历史 `scope.json.entity_ids` 设为当前运行股票池。下次 Run 用今天的股票池算 execute\_fp。如果池子和当年不同，会开新版本。

## CLI 命令

| 缩写    | 全称                        | 用途   |
| ----- | ------------------------- | ---- |
| `spn` | strategy\_pin\_version    | 固定版本 |
| `sup` | strategy\_unpin\_version  | 取消固定 |
| `sdv` | strategy\_delete\_version | 删除版本 |

