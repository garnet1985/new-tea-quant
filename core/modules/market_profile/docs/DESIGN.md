# Market Profile 设计说明

**版本：** `0.2.0`

## 挂载模型

`MarketRulesProxy` 在构造时实例化全部可用市场，再 `set_market` 选择当前挂载。调用方通过 `current` 或 `get_market` 取规则对象。

## 规则实现

各市场子类只提供 `profile_id` 与 `settings`；`MarketBaseRules` 用 Amplitude / Lot / Settlement 服务解释配置。

## 不做

- 不从包根导出自由函数（如历史 `get_market_profile`）
- 不在本模块读取策略配置文件
