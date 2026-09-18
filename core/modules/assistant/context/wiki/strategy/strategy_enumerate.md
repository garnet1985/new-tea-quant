---
title: NTQ 枚举机会
aliases:
  - enumerate
  - first step
  - 枚举
  - 第一步
  - 机会枚举
summary: 回测第一步：每个交易日对每只股票问有没有机会。
---

# 第一步：机会枚举

## 什么是枚举

枚举是回测的第一步。NTQ 在回测时间窗口内，每个交易日对每只股票调用一次策略钩子 `has_opportunity(ctx)`，返回 `True` 表示发现交易机会。

简单说：**你的策略在历史每一天、每只股票上，有没有发现机会？**

## 输出

枚举结果是一个 JSON 契约，后续三个引擎（价格因子、组合、决策者）都消费这份契约。

每条记录包含：

- 股票 ID

- 信号日期

- 信号快照（`signal_snapshot`）：用户在 `has_opportunity` 里通过 `ctx.capture(key, value)` 记录的值

## 报告

枚举报告回答这些问题：

- **总共发现了多少次机会？** 分布在多少只股票上？

- **机会的节奏分散度**：是集中在某些日期爆发，还是均匀分布？

- **可交易性**：涨停/跌停时触发的机会会被标记为不可交易

## 执行

枚举经回测引擎调度，支持两种模式：

- `entity_based`：按股票分组，每组独立跑完整时间线。适合少股票、长时间窗口

- `slice_based`：按时间切片，每片处理全部股票。适合多股票、中等时间窗口。slice\_based 有内存安全算法，按片从 DB 装载/释放，解决"全窗 10GB、内存 8GB"类问题

## 钩子

用户只需实现 `has_opportunity(ctx) -> bool`：

```python
def has_opportunity(self, ctx: StrategyContext) -> bool:
    data = ctx.data.items_with_meta()
    today = self.get_record_of_today(data, base_data_key=ctx.base_data_key)
    if today is None:
        return False
    rsi = today.get("rsi14")  # 来自 settings.data.base.indicators
    if rsi is None:
        return False
    ctx.capture("rsi", rsi)
    ctx.capture("close", today.get("close"))
    return rsi < 30
```

`ctx.data` 不是函数。序列是当天及之前的历史（前复权）。指标在 settings 声明后写在 K 线上，见 [用技术指标](../../know_how/use_indicators.md)。`ctx.capture()` 记入报告的信号快照。

## 关键设计

- **机会由框架构建**：钩子只返回 `True/False`，不要自己拼机会对象

- **signal\_snapshot**：命中时的归因记录，通过 `ctx.capture` 写入。不是 `ctx.remember`（那是易失内存袋，不落归因）

- **不复用旧枚举**：强制重跑（`--force`）时不会复用已有枚举产物，会重跑枚举

