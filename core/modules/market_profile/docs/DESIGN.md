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

### 决策 1：基类 + settings，不复制规则代码

**背景**  
多市场规则高度相似，复制易漂移。

**决策**  
`MarketBaseRules` 默认实现 + 各市场 `settings`；特殊逻辑再 override。

**理由**  
扩展成本低，行为集中。

**影响**  
settings schema 变更需同步基类校验默认值。

### 决策 2：跨模块只用 Facade 工厂

**背景**  
strategy 曾 deep-import `create_market_rules`。

**决策**  
公开 `MarketRulesProxy.for_market`；注册表工厂保留为内部。

**理由**  
单一入口、便于懒加载与日后替换实现。

**影响**  
旧 deep-import 需迁移（本轮已改）。

### 决策 3：Proxy 懒加载

**背景**  
构造时实例化全部市场无必要。

**决策**  
仅创建当前挂载市场；按需缓存。

**理由**  
启动更轻；行为对调用方透明。

**影响**  
`list_available` 只读注册表键，不触发实例化。
