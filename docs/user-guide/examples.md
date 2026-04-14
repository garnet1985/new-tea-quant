# 示例集合

本文档汇集了项目中的各种示例代码和教程。

## 策略示例

### Example 策略

位置：`userspace/strategies/example/`

完整的策略示例，包含：
- `strategy_worker.py` - 策略实现
- `settings.py` - 策略配置
- 完整的文档和注释

## 数据源示例

### Handler 示例

- `userspace/data_source/handlers/kline/` - K线数据 Handler
- `userspace/data_source/handlers/adj_factor_event/` - 复权因子事件 Handler
- `userspace/data_source/handlers/corporate_finance/` - 财务数据 Handler

### Provider 示例

- `userspace/data_source/providers/tushare/` - Tushare Provider
- `userspace/data_source/providers/akshare/` - AKShare Provider
- `userspace/data_source/providers/eastmoney/` - EastMoney Provider

### 快速开始教程

- [数据源用户指南](../../userspace/data_source/USER_GUIDE.md) - 手把手创建 Handler 教程

## 标签示例

### Momentum 标签场景

位置：`userspace/tags/momentum/`

完整的标签场景示例，包含：
- `tag_worker.py` - 标签计算逻辑
- `settings.py` - 场景配置
- README 文档

## 适配器示例

位置：`userspace/adapters/`

- `console/` - 控制台适配器
- `example/` - 示例适配器

模块说明与扩展约定见 [`core/modules/adapter/README.md`](../../core/modules/adapter/README.md)。

## 相关文档

- [策略开发指南](strategy-development.md)
- [数据源使用指南](data-source-usage.md)
- [标签系统指南](tag-system.md)
