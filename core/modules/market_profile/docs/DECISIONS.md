# modules.market_profile — 决定

**版本：** `0.2.0`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：决策 1：基类 + settings，不复制规则代码

**背景**  
多市场规则高度相似，复制易漂移。

**决策**  
`MarketBaseRules` 默认实现 + 各市场 `settings`；特殊逻辑再 override。

**理由**  
扩展成本低，行为集中。

**影响**  
settings schema 变更需同步基类校验默认值。

---

## DEC-02：决策 2：跨模块只用 Facade 工厂

**背景**  
strategy 曾 deep-import `create_market_rules`。

**决策**  
公开 `MarketRulesProxy.for_market`；注册表工厂保留为内部。

**理由**  
单一入口、便于懒加载与日后替换实现。

**影响**  
旧 deep-import 需迁移（本轮已改）。

---

## DEC-03：决策 3：Proxy 懒加载

**背景**  
构造时实例化全部市场无必要。

**决策**  
仅创建当前挂载市场；按需缓存。

**理由**  
启动更轻；行为对调用方透明。

**影响**  
`list_available` 只读注册表键，不触发实例化。


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
