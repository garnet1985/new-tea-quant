# 页面文档：`data-acquire.html`

## 这个页面是干什么的？
数据接入控制台，统一承载 Data Source、Data Contract、Tables 三类用户空间能力。

## 页面目的与用户价值
- 给用户一个“数据面”入口，降低配置和排障门槛。
- 在不开放高风险编辑的前提下，提供可观察、可调试、可执行的最小能力。
- 为后续 API 化提供清晰边界（哪些可改、哪些只读）。

## 页面功能描述
- 三个 tab：
  - **Data Source**：任务列表、状态、单项运行、运行全部、dry-run、启用/禁用、per-source 配置弹窗（handler/is_enabled/is_dry_run 等受控字段）。
  - **Data Contract**：只读列表 + per-contract 调试弹窗（data_key、entity_id、params、返回结构样例）。
  - **Tables**：统一 data grid（custom 在前，sys 在后），表名搜索、查看只读详情弹窗、新建 custom 表弹窗、仅 custom 支持删除（confirm）。
- 全局状态区与进度反馈（运行中/就绪、进度条、结果文本）。

## 页面假设与 Placeholder
- 所有执行和调试均为前端 mock，不触发真实数据任务。
- 表结构详情、数据总量、创建结果均为占位数据。
- 建表后默认只读，不支持编辑 schema（删除可用）。
