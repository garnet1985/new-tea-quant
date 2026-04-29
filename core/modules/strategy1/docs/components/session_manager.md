# 组件：SessionManager（会话 ID）

**版本：** `0.2.0`

## 职责

- 为 **`StrategyManager.simulate`** 生成单调递增的 **`session_id`**（如 `session_001`），并维护策略结果根目录下的 **`meta.json`**（下一序号、最后更新时间等）。

## 主要方法

- **`create_session() -> str`**：读 meta → 分配 id → 写回 meta。

## 使用场景

- 每次全量或采样回测可对应一个新 session，便于在 `simulations/` 下隔离多轮结果并与 **`OpportunityService`** 写入路径对齐。
