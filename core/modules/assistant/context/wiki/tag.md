---
title: Tag 标签系统
aliases:
  - tag
  - labeling
  - 标签
  - 打标签
  - 创建标签
summary: 配置驱动的标签：一次计算，多个策略可读。
---

# 标签

标签是可复用的资产层：一次算好写入库，多个策略都能读。

典型用途：市值等级、行业分类、RSI 区间，用来筛股票池或调参数。

| 特征 | 说明 |
| --- | --- |
| 两个文件 | `settings.py` + `tag.py` |
| 落库 | 写入 `sys_tag_value`，可增量更新 |
| 复用 | 一次计算，多个策略可读 |
| 怎么跑 | 由 `data.base` 的范围/类型决定：按股票、全局一份、或一次性静态表 |

## 用户文件

放在 `userspace/extensions/tags/<path>/`。

`settings.py` 声明身份、数据依赖、计算窗口和标签名；`tag.py` 实现 `calculate_tag`，返回 `{value, start_date?, end_date?}`，或 `None` 跳过写入。

步骤见 [如何创建标签](../know_how/create_tag.md)。

钩子可选 `on_calendar_asof`（按时间切片时的日历点）。上下文里有当天数据、实体、日历，以及增量时的 `prior_value`。

## 执行怎么选管道

由 `data.base` 决定：

| data.base | 怎么跑 |
| --- | --- |
| 非时序表 | 一次性算完 |
| 全局时序 | 主进程跑一份全局数据 |
| 逐股时序 | 走回测调度（按股票或按时间切片） |

更新模式：

| 模式 | 行为 |
| --- | --- |
| `incremental` | 只算上次进度之后，可用 `prior_value` |
| `refresh` | 删标签值和进度后重算 |
| `recompute=True` | 全量重建（值、定义、进度都删） |

CLI：`python cli.py t`。策略侧用 `ctx.data("tag")` 读已算好的标签。
