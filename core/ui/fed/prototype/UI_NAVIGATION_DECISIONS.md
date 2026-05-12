# NTQ Prototype 导航决策记录

更新时间：2026-04-23（setup-first 版本）

## 背景

当前原型目标：

1. 降低首次使用门槛（先完成系统就绪，再进入业务功能）
2. 支持两条高频路径（策略验证、机会扫描）
3. 专业能力集中管理，但避免用户在 UI 里直接改代码逻辑

## 导航方案结论

主导航采用 4 项：

- 策略工作台
- 机会扫描
- 高级功能
- 设置

补充一个系统前置页（非主导航常驻项）：

- `setup`：首次安装与必要配置引导页

## Setup-First 决策

### 触发条件

当系统检测到必要全局配置缺失时，业务页（工作台/扫描/高级）重定向到 `setup`：

- `db config` 缺失
- 其他必要 config 缺失（后续由后端定义完整检查清单）

### 引导目标

`setup` 负责“从不可用到可用”的一次性/低频流程：

1. 检查必需配置状态
2. 分步引导用户补齐配置
3. 校验成功后放行到主业务页

### Setup 结束后的归位

- 全局配置维护入口统一归到 `设置`
- `db config` 放在 `settings` 中维护（查看、测试连接、更新）

## 页面职责（与当前原型对齐）

### 策略工作台

- **列表页**（`workbench.html`）：展示策略与状态，点选进入单策略验证。
- **验证页**（`workbench-detail.html`）：双栏布局，顶栏支持当前策略动作（保存、克隆、启用/禁用、删除；占位）。
  - 页顶展示回测数据区间（显眼位置）
  - 三层执行计划：枚举机会 → 价格回测 → 资金模拟
  - 依赖关系：仅枚举为底座；价格与资金互不依赖
  - 样本股票位于执行计划下方，三层完成后解锁
- **单股 K 线**（`workbench-stock.html`）：独立页，三 Tab 对应三层标注意图（占位）

### 机会扫描

- 基于已启用策略批量扫描市场机会
- 支持严格模式 / 扫描演示模式
- 展示进度、报告、策略机会数与弹窗明细（占位）

### 高级功能（新分组）

目标：集中管理“可配置资产”，尽量避免 UI 直接改代码逻辑。

- **数据接入**
  - `data source`
  - `data contract`
  - `db tables`
- **标签因子**
  - `tag` 工作台
- **备份恢复**
  - `backup and migrate`

说明：

- `adapters` 暂不在 UI 暴露（功能未完备）
- 高级页以“配置管理”形态为主：查看、上传、验证、应用（占位）

### 设置

目标：系统级配置维护入口。

- `db config`（由 setup 完成首配后在此维护）
- 账户偏好、运行参数、环境连接配置

## 页面文件命名（当前）

- `prototype/workbench.html`
- `prototype/workbench-detail.html`
- `prototype/workbench-stock.html`
- `prototype/scan.html`
- `prototype/advanced.html`
- `prototype/settings.html`
- `prototype/setup.html`（新增：首次安装引导原型页）
- `prototype/backtest.html`（兼容跳转）

## 后续实施（React / API）

- 定义 setup 检查项协议（缺失项、错误码、可修复建议）
- 定义配置对象 schema（source/contract/tag/tables/backup）
- 定义配置验证与应用流程（校验、预览、回滚）
- 统一运行身份（`run_id`）与跨页面上下文传递

