---
title: NTQ 总览
aliases:
  - system overview
  - folder structure
  - architecture
  - module
  - 总览
  - 架构
summary: NTQ 是什么、目录怎么分、回测四步和配置落在哪。
---

# NTQ 概览

## NTQ 是什么

NTQ（New Tea Quant）是专注于 A 股的量化策略回测框架。核心理念：**把回测拆成四步，每步有独立报告，让你知道策略问题出在哪。**

- 版本：0.5.x（非正式版，API 不保证稳定）
- 语言：Python 3.9+
- 数据库：DuckDB（默认）/ MySQL / PostgreSQL
- 入口：`python launcher.py`（安装向导 + UI）、`python cli.py`（用户命令）、`python devcli.py`（开发命令）

## 目录（用户需要记住的）

```
new-tea-quant/
├── cli.py                      用户命令入口
├── core/                       框架代码，升级时被覆盖，不要改
├── userspace/                  你的数据，升级时保留
│   ├── strategies/             策略（strategy.py + settings.py）
│   │   ├── _template/          模板
│   │   ├── demo/               演示策略
│   │   └── settings_example.py 配置示例（带注释）
│   ├── extensions/             扩展：标签、数据契约、数据源、表、扫描适配器
│   └── system/                 系统配置、数据库文件、备份
├── initialization/             初始化数据包
└── docs/                       项目文档
```

策略在 `userspace/strategies/`，**不在** `userspace/extensions/`。

## 各块做什么

| 位置 | 职责 |
| --- | --- |
| CLI | 解析并执行 `python cli.py` 命令 |
| 数据库 | 连接、建表；默认 DuckDB 三个文件：行情 / 标签 / 策略产物 |
| 策略 | 枚举、价格因子、组合、扫描、归因 |
| 回测调度 | 按时间轴并行跑任务，不管策略业务含义 |
| 标签 | 一次计算，多个策略可读 |
| 数据契约 | 用数据键声明依赖；策略里 `ctx.data.items_with_meta()` 按键取数 |
| 数据源 | 从外部抓行情等 |
| 数据访问 | 按领域查数：股票 / 指数 / 宏观 / 日历 |
| 市场画像 | 涨跌停、手数、T+N |
| 扫描适配器 | 扫描结束后的后处理（报告、通知） |
| 助手 | AI 供应商配置与聊天 |

细节见对应 wiki，不要去 import 模块内部实现文件。

## 回测四步

```
枚举 → 每个交易日每只股票有没有机会
价格因子 → 每笔机会按成交假设和 goal 算单笔盈亏
组合 → 资金分配 + 纪律出场 → 净值与回撤
决策者 → 你自己选谁、买多少，再和程序化组合对比（独立命令）
```

`python cli.py s` 是价格因子 → 组合；枚举缺失才补跑。决策者 `sd`、归因 `sa` 是独立命令。缩写对照见约定文档。

## 用户空间

- `core/`：框架，升级覆盖
- `userspace/`：你的策略、扩展、配置、库文件，升级保留
- 系统配置：`userspace/system/config/`（`data.json`、数据库、可选 `worker.json`）
- 策略配置：`userspace/strategies/{name}/settings.py`，不和 `data.json` 合并；加载时补缺块默认值。目录名应等于 `meta.key`

## 版本

一次完整回测（枚举 + 价格因子 + 组合）对应一个 version，绑定时的生效设置指纹。环境变了（升级、钩子源码改了），旧版本变成仅供查阅。产物在 `{strategy}/results/simulations/{vid}/`，没有 `reports/`。`spn` / `sup` / `sdv` 固定、取消固定、删除版本——`spn` 不是跑回测。
