---
title: NTQ 设计原理
aliases:
  - design
  - philosophy
  - architecture
  - why NTQ
summary: NTQ 设计理念
---

# NTQ 设计原理

## 为什么做 NTQ

市面上的量化框架（Backtrader、Zipline 等）有一个共同特征：跑完回测只有一个最终结果——收益率、回撤、夏普。你不知道策略亏了是因为选股选错了、还是止盈止损设得不好、还是资金分配不合理。

NTQ 的核心设计动机是**策略诊断**：把回测拆成四步，每步有独立报告，让用户精确定位问题出在哪一层。

## 核心设计决策

### 1. 四步拆分，每步独立报告

枚举 → 价格因子 → 组合 → 决策者。这不是简单的 pipeline 分阶段执行，而是**每步产出独立的诊断报告**。

- 第一步告诉你"有没有找到机会"

- 第二步告诉你"单笔交易赚不赚"

- 第三步告诉你"整体账户表现如何"

- 第四步告诉你"你的判断和代码的判断差多少"

其他框架把这三件事揉在一个 cerebro 里跑，你只知道结果好不好，不知道为什么好或为什么不好。

### 2. 声明式策略配置

用户写 `settings.py` 而不是继承一堆基类。配置是一个 Python 字典，大部分时候当 JSON 写。

- 好处：低门槛，不需要学一套面向对象体系

- 设计取舍：settings.py 是 Python 文件而非纯 JSON，允许高级用户写动态逻辑（如从环境变量读阈值）。这牺牲了一定的可序列化性，换取了灵活性。版本系统通过白名单抽取 effective settings 来解决哈希问题

### 3. Userspace 隔离

`core/` 是框架代码，升级时被覆盖。`userspace/` 是用户数据，升级时保留。

- 所有用户自定义内容（策略、标签、数据契约、数据源、表、适配器）在 `userspace/extensions/` 下

- 所有系统配置在 `userspace/system/` 下

- 升级方式：下载新代码，保留 userspace，其他文件替换

### 4. Facade 模式统一

每个模块对外只暴露一个入口类：`Strategy`、`Tag`、`ContractIssuer`、`DataManager`、`BacktestEngine`、`Adapter`、`Indicator`、`MarketRulesProxy`、`Assistant`。

- 用户不需要知道内部有多少层

- 跨模块不 deep-import 内部实现，优先 Facade

- 契约类型从 `contracts.py` 导入

### 5. 数据合约 + 自动路由

数据不是直接 SQL 查表，而是通过 DataKey 声明数据依赖。DataKey 决定数据路由模式：

- `stock.kline.daily` → 逐股逐日（per\_entity）→ 走 BacktestEngine 多进程

- `market.index.daily` → 全局单份（global）→ 主进程推进

- 静态表 → 不按时间遍历（non\_time\_series）

这让 tag 和 strategy 可以复用同一个回测引擎，只是数据路由不同。

### 6. 版本指纹系统

每次完整回测产生一个版本，版本绑定当时的 effective settings 指纹。指纹分两种：

- `execute_fp`：可逆的执行输入（白名单 settings + 本次股票池）

- `env_fp`：不可逆的执行环境（NTQ 版本、hooks 源码、DB 类型、data\_contract 映射）

环境变了，旧版本变为"仅供查阅"状态。这让用户可以对比不同版本的报告，同时清楚哪些版本还能继续跑、哪些不能。

## 明确不做的事

- **不做实盘交易**：NTQ 是研究工具，不连接券商接口

- **不提供数据认证**：用户自己对接 tushare 等数据源

- **不预测涨跌**：只帮用户验证策略逻辑

- **不做云端托管**：单机运行，数据在本地

