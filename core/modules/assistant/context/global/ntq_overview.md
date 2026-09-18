---
title: NTQ 总览
aliases:
  - system overview
  - folder structure
  - architecture
  - module
summary: 了解NTQ是什么，什么样的架构，结构。系统的总览。
---

# NTQ 架构概览

## NTQ 是什么

NTQ（New Tea Quant）是专注于 A 股市场的量化策略回测框架。核心理念：**把回测拆成四步，每步有独立报告，让你知道策略问题出在哪。**

- 版本：0.5.x（非正式版，API 不保证稳定）

- 语言：Python 3.9+

- 数据库：DuckDB（默认）/ MySQL / PostgreSQL

- 许可证：Apache 2.0

- 入口：`cli.py`（用户命令）、`devcli.py`（开发命令）

## 目录结构

```
new-tea-quant/
├── cli.py                    # 用户 CLI 入口
├── devcli.py                  # 开发 CLI 入口
├── install.py                 # 安装脚本
├── launcher.py                # UI 启动器
├── core/                      # 框架核心（升级时被覆盖）
│   ├── system.json            # 版本元信息
│   ├── system.py              # 版本加载逻辑
│   ├── infra/                 # 基础设施层（无业务逻辑）
│   │   ├── cli/               # CLI 实现（user/ + dev/）
│   │   ├── db/                # 数据库连接与 schema 管理
│   │   ├── discovery/         # 文件/类自动发现
│   │   ├── project_context/   # 项目路径上下文
│   │   ├── setup/             # 安装流程
│   │   ├── cmd_layout/        # CLI 输出布局
│   │   ├── export_import/     # 策略包导入导出
│   │   ├── trace/             # 追踪框架
│   │   ├── task_guard/        # 租约机制
│   │   ├── feedback/          # 反馈提交
│   │   ├── machine_capacity/  # 硬件探测
│   │   ├── updater/           # 框架升级
│   │   └── utils/             # 通用工具
│   ├── modules/               # 业务模块层（有量化领域逻辑）
│   │   ├── strategy/          # 策略执行（四步引擎）
│   │   ├── backtest_engine/  # 回测调度引擎
│   │   ├── tag/               # 标签资产层
│   │   ├── data_contract/     # 数据契约签发
│   │   ├── data_source/       # 外部数据抓取
│   │   ├── data_manager/      # 统一数据访问门面
│   │   ├── indicator/         # 技术指标计算代理
│   │   ├── market_profile/    # 市场制度规则
│   │   ├── analysis/          # 统计/ML 原语工具箱
│   │   ├── adapter/           # 扫描结果适配器
│   │   └── assistant/        # AI 供应商配置
│   ├── tables/                # 内置数据表 schema
│   │   ├── stock/             # 股票相关表
│   │   ├── index/             # 指数相关表
│   │   ├── macro/             # 宏观相关表
│   │   ├── calendar/          # 交易日历表
│   │   ├── tag/               # 标签存储表
│   │   └── system/            # 系统表
│   ├── default_config/        # 默认配置文件
│   │   └── database/          # 数据库默认配置
│   ├── bff/                   # 后端 API（UI 用）
│   └── ui/                    # 前端 UI
│
├── userspace/                 # 用户空间（升级时保留）
│   ├── strategies/            # 用户策略
│   │   ├── _template/         # 策略模板
│   │   ├── demo/              # 演示策略
│   │   └── settings_example.py  # 配置示例（带详细注释）
│   ├── extensions/            # 用户扩展
│   │   ├── strategies/        # 策略扩展（hooks + settings）
│   │   ├── tags/              # 标签场景
│   │   ├── data_contract/     # 自定义数据契约
│   │   ├── data_source/       # 自定义数据源
│   │   ├── tables/            # 自定义数据表
│   │   ├── adapters/          # 扫描结果适配器
│   │   └── assistant/         # AI 供应商配置
│   └── system/                # 系统级配置
│       ├── config/            # data.json / database 配置
│       ├── db/                # DuckDB 数据库文件
│       ├── backup/            # 备份
│       └── updater/           # 升级缓存
│
├── initialization/            # 初始化数据
│   └── data/                  # 数据包 zip
├── docs/                      # 项目文档
├── ci/                        # CI 配置
└── requirements.txt           # Python 依赖
```

## 核心模块职责

### infra 层（无业务，通用基础设施）

| 模块                | 门面/入口                  | 职责                       |
| ----------------- | ---------------------- | ------------------------ |
| `cli`             | `Cli.user` / `Cli.dev` | CLI 命令解析与执行              |
| `db`              | `DatabaseManager`      | 数据库连接、schema 管理、表初始化     |
| `discovery`       | -                      | 文件/类自动发现机制               |
| `project_context` | `ProjectContext`       | 项目路径上下文（所有路径从这里取）        |
| `setup`           | -                      | 安装流程（导入数据、初始化 userspace） |
| `export_import`   | -                      | 策略包打包与安装                 |

### modules 层（有业务，量化领域逻辑）

| 模块                | 门面                  | 职责                                       |
| ----------------- | ------------------- | ---------------------------------------- |
| `strategy`        | `Strategy`          | 策略执行：枚举、价格因子、组合模拟、扫描、归因分析                |
| `backtest_engine` | `BacktestEngine`    | 回测调度引擎：probe → plan → execute → monitor  |
| `tag`             | `Tag`               | 标签计算与落库，供策略复用                            |
| `data_contract`   | `ContractIssuer`    | 数据契约签发：DataKey 白名单与三层契约结构                |
| `data_source`     | `DataSourceManager` | 外部数据抓取：按 handler + provider 模式组织         |
| `data_manager`    | `DataManager`       | 统一数据访问门面：stock/index/macro/calendar 领域服务 |
| `indicator`       | `Indicator`         | 技术指标计算代理（pandas-ta-classic 薄封装）          |
| `market_profile`  | `MarketRulesProxy`  | 市场制度规则：涨跌幅、整手、T+N 交收                     |
| `analysis`        | `Analysis`          | 统计/ML 原语工具箱（纯函数，无 I/O）                   |
| `adapter`         | `Adapter`           | 扫描结果适配器：机会列表交给 userspace 处理              |
| `assistant`       | `Assistant`         | AI 供应商配置与聊天                              |

## 回测四步流程

NTQ 的核心设计是四步拆分，每步独立产出报告：

```
第一步：枚举（Enumerate）
  输入：策略钩子 has_opportunity + 历史数据
  输出：每个交易日每只股票是否有机会
  报告：机会概览、分布、节奏分散度、可交易性

第二步：价格因子（Price Factor）
  输入：枚举结果 + 入场/出场假设
  输出：每笔交易的单笔盈亏
  报告：胜率、盈亏比、持仓周期、ROI 分布

第三步：组合模拟（Portfolio）
  输入：价格因子结果 + 资金管理 + 止盈止损
  输出：组合层面的净值曲线和回撤
  报告：账户总览、胜率盈亏、回撤、净值曲线

第四步：决策者模式（Decision Maker）
  输入：枚举结果 + 用户手动抉择
  输出：用户作为决策者的组合表现
  报告：与程序化组合的对比报告
```

CLI 命令对应：

| 步骤  | 命令                             | 缩写   |
| --- | ------------------------------ | ---- |
| 第一步 | `cli.py strategy_enumerate`    | `se` |
| 第二步 | `cli.py strategy_price_factor` | `sp` |
| 第三步 | `cli.py strategy_portfolio`    | `so` |
| 第四步 | `cli.py strategy_decision`     | `sd` |
| 全部  | `cli.py strategy_simulate`     | `s`  |
| 扫描  | `cli.py scan`                  | `c`  |
| 归因  | `cli.py strategy_analyze`      | `sa` |

## 用户空间隔离原则

- `core/` = 框架代码，升级时被覆盖，用户不应修改

- `userspace/` = 用户数据，升级时保留，所有自定义内容放这里

- `userspace/extensions/` = 用户扩展（策略、标签、数据契约、数据源、表、适配器）

- `userspace/system/config/` = 系统配置（data.json、database 配置）

- `userspace/system/db/` = DuckDB 数据库文件

## 配置体系

| 配置文件                  | 位置                                        | 作用              | 合并规则     |
| --------------------- | ----------------------------------------- | --------------- | -------- |
| `data.json`           | `userspace/system/config/`                | 数据设置（起始日期、股票池等） | 深度合并     |
| `common.json`         | `userspace/system/config/database/`       | 数据库类型选择         | 深度合并     |
| `{db_type}.json`      | `userspace/system/config/database/`       | 数据库连接参数         | 深度合并     |
| `worker.json`         | `userspace/system/config/`                | 回测性能参数          | 深度合并     |
| `settings.py`         | `userspace/extensions/strategies/{name}/` | 策略配置            | 不合并，独立文件 |
| `settings_example.py` | `userspace/strategies/`                   | 配置示例与注释参考       | 只读       |

## 版本与指纹

- 每次完整回测产生一个版本，版本绑定当时的 effective settings 指纹

- 指纹 = effective settings 白名单字段 + 引擎版本 + 数据快照哈希

- 版本可 pin（固定不被清理）和 unpin

- 环境指纹变化时，旧版本变为"仅供查阅"状态，无法继续运行

- CLI：`spn`（pin）、`sup`（unpin）、`sdv`（delete version）

## 数据流

```
外部数据源（tushare 等）
    ↓ data_source 模块抓取
数据表（stock/index/macro/calendar）
    ↓ data_contract 签发 DataKey
策略钩子 ctx.data("stock.kline.daily")
    ↓ has_opportunity 判断
枚举结果（机会列表）
    ↓ price_factor 引擎模拟单笔交易
价格因子报告
    ↓ portfolio 引擎分配资金 + 止盈止损
组合报告
    ↓ analyzer 归因分析
归因报告
    ↓ scanner 扫描实时行情
扫描结果 → adapter 通知用户
```

