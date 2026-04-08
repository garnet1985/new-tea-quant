# Data Contract 模块（全局）

## 目标

`data_contract` 是一个**全局模块**，负责把“外部/裸数据（Raw Data）”通过一套可重复、可审计的流程，**签发**为“满足契约的标准数据（Contracted Data）”。

> 重要：`data_contract` **不关心**数据来自哪里、谁来喂、怎么喂（DB/API/文件/手工导入都可以）。  
> 它只关心：输入是否满足契约；不满足就 fail-closed（明确失败），满足则输出标准结果。

## 非目标（MVP）

- 不负责 query / join / DataManager 的加载逻辑
- 不负责写入数据库（导入/灌库属于其他模块）
- 不做“通用用户表适配系统”（MVP 仅覆盖我们当前需要的契约）

## 核心概念

- **ContractConfig**：契约配置（字段、时间轴、required 等）
- **Contract（契约）**：可执行的规则集合（校验、规范化、裁剪等）
- **ContractManager（签发者/管理者）**：读取 config、签发 contract、管理生命周期与入口 API
- **Raw Data**：未被信任的数据输入（结构可能不一致、字段可能缺失、格式不确定）
- **Contracted Data**：通过契约签发后的输出（结构/字段/时间轴符合约定）

## 输入 / 输出（建议接口形态）

### 输入

- `raw_data`：`List[Dict[str, Any]]` 或其他可迭代记录集
- `config`：`ContractConfig`
- `context`：可选上下文（例如：时间范围、entity_id、策略名等）

### 输出

- 成功：`ContractedData`（可继续被上层模块消费/注入）
- 失败：抛出 `ContractViolationError`（fail-closed，错误信息要面向用户）

## 责任边界（约束原则）

- **Contract 不做 IO**：不直接访问 DB / 文件 / 网络
- **ContractManager 做编排**：决定“何时校验、校验什么、失败如何表达”
- **上游负责喂 Raw Data**：DataSource / DataManager / Installer 等提供 raw_data
- **下游只接收 Contracted Data**：Strategy/Tag/Indicator 等模块不再各写一套“自定义校验”

## 推荐目录结构（待实现）

> 本 README 先落地模块骨架；后续实现按模块习惯补齐 manager / contracts / helper。

- `contract_manager.py`：读取 config、签发、管理入口
- `contracts/`：契约定义（可复数）
- `models/`：契约相关数据结构（config/spec/result）
- `helper/`：时间轴、schema 等通用工具
- `errors.py`：统一异常（ContractViolationError 等）

## MVP 计划（建议）

优先做“能立刻解决现有痛点”的契约：

- **TagScenarioContract**：策略依赖的 tag scenario 必须存在，否则在 preprocess 阶段 fail-fast
- **KlineContract**：K 线必须具备时间轴字段（`date`），且可被裁剪/排序（用于枚举/模拟一致性）

