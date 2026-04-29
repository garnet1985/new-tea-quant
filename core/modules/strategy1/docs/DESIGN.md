# Strategy 设计说明

**版本：** `0.2.0`

---

## 四层关系（摘要）

1. **OpportunityEnumerator**：全区间、全标的（或采样集）**完整枚举**；多路径、多未完成 target 可并存；输出 **CSV**，供下游一次性加载。
2. **Scanner / StrategyManager.scan**：通常只关心**最近交易日**；每股票一 Job；结果 **JSON**，可接 Adapter。
3. **PriceFactorSimulator**：读取枚举输出，按股并行算「价格层」结果；**无**账户级资金耦合。
4. **CapitalAllocationSimulator**：从 CSV 构建 **Event** 时间轴，**单进程**更新 **Account**，含费用与仓位规则。

组件级说明见 **[docs/components/](components/README.md)**。

---

## Settings 两层结构

- **`StrategySettings`（`data_classes`）**：构造时对 **`raw_settings`** 深拷贝，并挂载 **`meta` / `data` / `scanner` / `enumerator` / `price_simulator` / `capital_allocation` / `sampling` / `goal`** 等块；**`validate()`** 在策略发现阶段统一调用。
- **各块 `Strategy*Settings`**：只读语义为主，**`to_dict()`** 用于序列化进 Job payload。

---

## 执行与并发

- **多进程**：`StrategyManager`的 scan/simulate、**OpportunityEnumerator**、**PriceFactorSimulator**（按股票独立）。
- **单进程**：**CapitalAllocationSimulator**（全局状态）。

---

## 版本与目录

- **VersionManager** + **ResultPathManager**：枚举版本、模拟器版本、`latest` 解析与 **自动补跑枚举** 规则与路径一致；细节见 `managers/` 与各模拟器内 `_resolve_or_build_enum_version`。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API.md](API.md)
- [DECISIONS.md](DECISIONS.md)
