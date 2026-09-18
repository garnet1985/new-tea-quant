---
title: create tag 创建标签
aliases:
  - tag
  - create
  - 标签
  - 创建标签
  - 打标签
summary: 新建标签场景：settings.py + tag.py，以及 CLI `t`。
---


# 如何创建标签

## 从模板创建

```bash
python cli.py t -n my_tag
```

会在 `userspace/extensions/tags/my_tag/` 下生成 `settings.py` 和 `tag.py`。

## 两个文件

| 文件            | 职责                                    |
| ------------- | ------------------------------------- |
| `settings.py` | 标签配置（数据源、计算模式、定义列表）                   |
| `tag.py`      | 标签钩子，继承 `TagHooks`，实现 `calculate_tag` |

## settings.py

```python
settings = {
    "is_enabled": True,
    "meta": {
        "key": "market_cap_tier",
        "display_name": "市值等级",
        "description": "按总市值分为大/中/小盘",
    },
    "data": {
        "base": {"data_key": "stock.kline.daily"},
        "required": [],
        "min_required_records": 1,
    },
    "calculation": {
        "execution": {"mode": "entity_based"},
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "update_mode": "incremental",
    },
    "tag_definitions": [
        {"name": "large_cap", "display_name": "大盘", "description": "市值>500亿"},
        {"name": "mid_cap", "display_name": "中盘", "description": "市值100-500亿"},
        {"name": "small_cap", "display_name": "小盘", "description": "市值<100亿"},
    ],
}
```

### 关键字段

| 字段                           | 说明                                               |
| ---------------------------- | ------------------------------------------------ |
| `meta.key`                   | 标签唯一标识                                           |
| `data.base.data_key`         | 决定路由模式（per\_entity / global / non\_time\_series） |
| `calculation.execution.mode` | `entity_based` 或 `slice_based`（仅 per\_entity 需要） |
| `calculation.update_mode`    | `incremental` / `refresh`                        |
| `calculation.recompute`      | True = 全量重建                                      |
| `tag_definitions`            | 标签定义列表                                           |

### data.base 路由

| data.base 特征               | 路由             | 说明                         |
| -------------------------- | -------------- | -------------------------- |
| per\_entity + time\_series | BacktestEngine | 逐股逐日计算                     |
| global + time\_series      | 主进程            | 全局单份，sentinel `__global__` |
| non\_time\_series          | 主进程一次性         | 不按时间遍历                     |

## tag.py

```python
from core.modules.tag.contracts import TagContext, TagHooks

class MarketCapTagHooks(TagHooks):
    def calculate_tag(self, ctx: TagContext) -> dict | None:
        klines = ctx.data.items.get(ctx.base_data_key, [])
        if not klines:
            return None

        last_bar = klines[-1]
        market_cap = last_bar.get("total_market_cap")

        if market_cap is None:
            return None

        if market_cap > 500e8:
            tier = "large_cap"
        elif market_cap > 100e8:
            tier = "mid_cap"
        else:
            tier = "small_cap"

        return {
            "value": tier,
            "start_date": last_bar["date"],
            "end_date": last_bar["date"],
        }
```

### calculate\_tag 返回值

| 返回                                                   | 说明      |
| ---------------------------------------------------- | ------- |
| `{"value": ..., "start_date": ..., "end_date": ...}` | 正常写入标签值 |
| `None`                                               | 跳过，不写入  |

`value` 可以是字符串、数字、字典、列表——存为 JSON。

### ctx.data 常用字段

| 字段                        | 说明                |
| ------------------------- | ----------------- |
| `ctx.data.now`            | 当前日期              |
| `ctx.data.entity_id`      | 当前实体 ID           |
| `ctx.data.items`          | 按 data\_key 分组的数据 |
| `ctx.data.tag_definition` | 当前标签定义            |
| `ctx.data.prior_value`    | 上次计算的值（增量热启动）     |

## non\_time\_series 标签示例

对于不按时间遍历的标签（如经济区归类），`data.base` 用 `stock.list`：

```python
settings = {
    "data": {
        "base": {"data_key": "stock.list"},
        "min_required_records": 0,
    },
    "calculation": {
        "update_mode": "refresh",
        "recompute": True,
    },
    "tag_definitions": [
        {"name": "stock_area_cluster", "display_name": "经济区归类", "description": "..."},
    ],
}
```

tag.py 的 `calculate_tag` 一次性处理全部股票，返回一个聚合结果。

## 运行标签

```bash
# 运行所有已启用标签
python cli.py t

# 运行指定标签
python cli.py t --scenario market_cap_tier

# 试运行（不落库）
python cli.py t --dry-run

# 只跑前 N 个实体（试验用）
python cli.py t --entity-limit 5

# 列出已发现的标签
python cli.py t --list
```

## Python API

```python
from core.modules.tag import Tag

tag = Tag()
tag.refresh()
tag.execute(scenario_name="market_cap_tier")
```

## 数据库表

标签计算结果写入：

| 表                       | 内容                                                              |
| ----------------------- | --------------------------------------------------------------- |
| `sys_tag_scenario`      | 场景元数据                                                           |
| `sys_tag_definition`    | 标签定义                                                            |
| `sys_tag_value`         | 标签值（entity\_id, tag\_definition\_id, as\_of\_date, json\_value） |
| `sys_tag_calc_progress` | 增量计算水位线                                                         |

## 策略中使用标签

在策略 settings.py 的 `data.required` 中声明：

```python
"data": {
    "required": [
        {"data_key": "tag", "params": {"tag_scenario": "market_cap_tier"}},
    ],
}
```

策略钩子中通过 `ctx.data.items_with_meta().get("tag")` 读取标签数据。
