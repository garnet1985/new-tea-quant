---
title: Adapter 机会适配
aliases:
  - adapter
  - opportunity
  - scanner
  - extension
  - 适配器
  - 机会适配
  - 扫描后处理
summary: 扫描结束后的机会后处理：不是券商或数据源适配器。
---

# 适配器：扫描结果后处理

适配器是扫描结束后的后处理。策略扫完当天机会后，框架把机会列表交给你写的适配器。

典型用途：按行业分组出报告、发通知、二次筛选或排序。

> 这不是券商或数据源适配器。它不接行情、不下单，只处理扫描结果。

## 放哪、怎么挂

目录：`userspace/extensions/adapters/<name>/`

- `adapter.py`：实现 `process(opportunities, context)`
- `settings.py`：可选；基类会读进 `self.config`

策略 `settings.py`：

```python
"scanner": {
    "adapters": "industry_report",
    # 或多个："adapters": ["industry_report", "notification"],
}
```

扫描按 `scanner.adapters` 加载。没配适配器就打印默认摘要；配了就按顺序调用 `process`；全部失败再回退默认摘要。

写法见 [如何编写适配器](../know_how/write_adapter.md)。

## 约束

| 规则 | 说明 |
| --- | --- |
| 只读传入的 context | 不要去 import 策略模块 |
| 输出不影响回测 | 报告或外部通知，不改回测结果 |
| 多个按配置顺序跑 | 各自处理同一份机会列表 |
| 失败回退 | 全部失败时打印默认摘要 |
