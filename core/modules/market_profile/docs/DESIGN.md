# Market Profile 设计说明

**版本：** `0.2.0`

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## 挂载模型

- **`MarketRulesProxy.for_market(id)`**：只创建目标市场（跨模块推荐）。
- **实例 Proxy**：构造时挂载 `default_market`；其它市场在 `get_market` / `set_market` 时懒加载，同实例内缓存。

## 规则实现

各市场子类只提供 `profile_id` 与 `settings`；`MarketBaseRules` 用 Amplitude / Lot / Settlement 服务解释配置；代码匹配走 `MatchingService`。

## 不做

- 不从包根导出自由函数（历史 `get_market_profile` 已删）
- 不把 `create_market_rules` 当作跨模块 API（内部工厂；对外用 `for_market`）
- 不在本模块读取策略配置文件
- 本模块当前**无** userspace 覆盖加载路径（changelog 历史表述已纠正）

---

## 设计决策

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）