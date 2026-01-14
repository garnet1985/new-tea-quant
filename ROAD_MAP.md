#!/usr/bin/env python3
# Road Map

next version：v0.1.1

## 1. 目录与分层重构（未来迭代）

- **userspace 提升到根目录**
  - 现状：`app/userspace/`（策略代码 + 结果数据混在 app 目录下）
  - 目标：`/userspace/` 与 `app/` 平级，形成「框架 (app/core) vs 用户空间 (userspace)」的清晰边界。
  - 好处：
    - 未来可以单独发布 `app/core` 为库（如 `stocks_core`），用户仓库主要维护 `userspace/`。
    - 升级框架时，可以明确说明：只覆盖 `app/core`，不动 `userspace/`。
  - 注意：需要配一份迁移指南和（可选）小脚本，避免手动移动大量结果数据出错。

- **结果数据路径可配置 / 可迁移**
  - 抽象结果目录（`results/`, `scan_cache/` 等）的 base path，支持指向外部数据盘或挂载卷。
  - 升级代码仓时，仅更新代码，不强制搬动历史数据。

- **utils 收拢到 core**
  - 现状：根目录 `utils/` 下有通用工具（`util.py`, `warning_suppressor.py`）。
  - 目标：将框架内部使用的工具迁移到 `app/core/utils/` 或合适的 core 子模块中：
    - 统一从 `app.core.utils...` 引用。
  - 根目录 `utils/` 未来只保留纯脚本级工具（如有必要），否则考虑删除。

## 2. bff / fed 升级策略（规划）

- 将 **bff / fed** 视为“使用 core 的应用”，而非 core 的一部分：
  - `bff/`：后端 BFF 层，依赖 `app/core` 提供 HTTP API。
  - `fed/`：前端应用，依赖 bff API。

- 升级策略：
  - 核心库（`app/core`）保证对外 API 尽量后向兼容，重要变更记录在 changelog / 文档中。
  - 官方维护一套 `bff` / `fed` 参考实现 / 模板：
    - 用户可以直接使用官方版本（升级时覆盖更新），或在此基础上做少量二次开发。
    - 未来可拆分为独立仓：`stocks-core` / `stocks-bff` / `stocks-fed`。

## 3. Strategy 模块后续工作（参考 REFACTOR_TODO）

- **API 收敛 & 调用示例**
  - 在 `strategy_manager.py` 或上层 BFF 中，提供统一的调用入口示例：
    - `OpportunityEnumerator.enumerate(...)`
    - `PriceFactorSimulator.run(strategy_name)`
    - `CapitalAllocationSimulator.run(strategy_name)`
    - `Scanner.scan(...)`

- **文档对齐**
  - 更新 `ARCHITECTURE_DESIGN.md` 与 `DESIGN.md`，同步当前实现。
  - 为 `BaseStrategyWorker` 钩子编写“方法一览表 + 调用时机”文档。
  - 在 README / Quick Start 中加一条“从写一个策略到跑完整回测”的流水线示例。

next version：v0.1.2

## 1. 优化入口文件

## 2. 增加worker的监控器，保证运行时不会内存爆炸或者CPU过载，更加智能的worker计算器

## 3. Provider迁移进userspace，变成可插拔

## 4. 整理全局枚举，分清楚scope

## 5. 整理全局config，统一命名

## 6. 支持start.py -i 默认import demo数据CSV



next version：v0.1.3

## 1. UT覆盖率达到80%

## 2. 每个模块都有readme和architecture文档

## 3. 优化debug体验



next version：v0.2.1 （开源后）

## 1. 支持market environment配置

## 2. 支持配置价格基准（目前是按照close价格）

## 3. 支持做空（非A股专用）



next version：v0.2.2

## 1. UI支持可视化



next version：v0.3.1

## 1. 加强机器学习模块

## 2. 加强数据可视化

## 3. 初始UI + BFF



next version：v0.3.2

## 1. 提供在线数据renew服务（会员业务）