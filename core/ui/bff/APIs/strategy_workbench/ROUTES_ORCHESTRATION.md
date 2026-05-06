# 策略工作台 BFF：`routes` 编排层约定

> **重做说明**：策略工作台正按 **V2 从零规划**，请先阅读  
> [`core/ui/fed/src/pages/strategyWorkbenchPage/REDESIGN_PLAN.md`](../../../../fed/src/pages/strategyWorkbenchPage/REDESIGN_PLAN.md)  
> 契约以同目录前端侧的 [`API.md`](../../../../fed/src/pages/strategyWorkbenchPage/API.md) 为准。  
> **下文不再维护「旧实现逐步骤对照」**；待 **REDESIGN_PLAN 阶段 3** 定稿后，在此文件按 V2 路由重写每张步骤表。

## 原则（延续）

- **编排层（routes）**：解析输入、按顺序调用下层能力、组装 HTTP 响应；步骤在代码里可读。
- **实现层**：业务规则与 IO 不在 routes 展开成大段逻辑。
- **一步一事**：有几步写几步。

## 待填充：V2 路由 × 编排步骤

| V2 编号 | 方法 | 路径（逻辑名，前缀待定） | 编排步骤（Step 1 …） |
|---------|------|--------------------------|----------------------|
| V2-01 | GET | `/strategy/{strategy_name}/version/latest` | *待填* |
| V2-02 | GET | `/strategies/list` | *待填* |
| V2-03 | GET | `/strategy/{strategy_name}/versions` | *待填* |
| V2-04 | GET | 各选项类子路径 | *待填* |
| V2-05 | POST | `/strategy/{strategy_name}/{step}/run` | *待填* |
| V2-06 | GET | `/strategy/{strategy_name}/{step}/progress` | *待填* |
| V2-07 | GET | `/strategy/{strategy_name}/{step}/report`（query：必填 `version_id`） | *待填* |
| V2-08 | GET | `/strategy/{strategy_name}/version/{version_id}` | *待填* |
| V2-09 | POST | `/strategy/{strategy_name}/apply-settings/{version_id}` | *待填* |

实现时再增加：错误分支、与 Flask 注册前缀（如 `/v1/...`）的最终拼接规则。
