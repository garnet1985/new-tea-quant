# Market Profile（`modules.market_profile`）

为 NTQ 提供多市场制度规则（涨跌幅、整手、交收等）。对外门面为 `MarketRulesProxy`；规则基类见 `contracts`。

## 适用场景

- 策略/组合在交易规则判断前挂载目标市场
- 读取涨跌停价、整手数量、T+N 交收

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.market_profile import MarketRulesProxy`。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
