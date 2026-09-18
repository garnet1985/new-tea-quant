---
title: Tag 标签系统
aliases:
  - tag
  - labeling
  - flag
  - classification
  - backtest engine
  - reusable factor
summary: NTQ的标签系统介绍。
---

# 标签系统：Tag

## 什么是 Tag

Tag 是 NTQ 的标签资产层。它提供**配置驱动的标签计算和数据库持久化**，可被策略复用。

典型用途：给股票打上"市值等级"、"行业分类"、"RSI 区间"等标签，策略通过标签筛选股票池或调整参数。

| 特征   | 说明                                   |
| ---- | ------------------------------------ |
| 配置驱动 | `settings.py` + `tag.py` 两文件定义一个标签场景 |
| 持久化  | 标签值写入 `sys_tag_value` 表，可增量更新        |
| 复用   | 一次计算，多个策略可读                          |
| 路由   | 按 `data.base` 的 scope/type 自动选择执行管道  |

## 架构

```
Tag 门面 (core/tag.py)
  ├── DiscoveryService — 磁盘扫描 + 验证
  ├── TagSettings — 配置校验 / 默认值
  ├── MetadataEnsureService — DB 元数据同步
  ├── TagEntityListResolver — 实体池解析
  │
  └── 按 data.base 路由：
      ├── per_entity → BacktestEngine (entity_based / slice_based)
      ├── global → 轻量主进程运行器 (sentinel entity __global__)
      └── non_time_series → 一次性主进程计算
```

门面是唯一公共入口：

```python
from core.modules.tag import Tag
from core.modules.tag.contracts import TagHooks, TagContext
```

## 用户侧文件

用户在 `userspace/extensions/tags/<path>/` 下创建两个文件：

### settings.py

```python
settings = {
    "meta": {
        "key": "market_cap_tier",
        "display_name": "市值等级",
        "description": "按总市值分为大/中/小盘",
    },
    "data": {
        "base": {"data_key": "stock.kline.daily"},
        "required": [
            {"data_key": "stock.finance.quarterly"},
        ],
        "min_required_records": 1,
    },
    "calculation": {
        "execution": {"mode": "entity_based"},
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "update_mode": "incremental",
        "dry_run": False,
    },
    "tag_definitions": [
        {"name": "large_cap", "display_name": "大盘", "description": "市值>500亿"},
        {"name": "mid_cap", "display_name": "中盘", "description": "市值100-500亿"},
        {"name": "small_cap", "display_name": "小盘", "description": "市值<100亿"},
    ],
    "is_enabled": True,
}
```

### tag.py

```python
from core.modules.tag.contracts import TagHooks, TagContext

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

### TagHooks 接口

| 方法                                | 必须 | 说明                                                 |
| --------------------------------- | -- | -------------------------------------------------- |
| `calculate_tag(ctx) -> dict/None` | 是  | 返回 `{value, start_date?, end_date?}` 或 `None` 跳过写入 |
| `on_calendar_asof(ctx)`           | 否  | slice\_based 模式下的日历点钩子                             |

### TagContext

| 数据块            | 内容                                                                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `ctx.tag`      | 标签身份信息（key/path）                                                                                                                     |
| `ctx.settings` | 完整设置对象                                                                                                                               |
| `ctx.data`     | 只读运行时数据：`now`、`entity_list`、`entity_id`、`items`（按 data\_key 分组）、`by_entity`（slice用）、`calendar`、`tag_definition`、`prior_value`（增量热启动） |
| `ctx.custom`   | 钩子间传递的可变字典                                                                                                                           |

## 执行路由

`data.base` 的 scope 和 type 决定执行管道：

| data.base 特征                            | 路由                | 管道                                         |
| --------------------------------------- | ----------------- | ------------------------------------------ |
| `non_time_series` type                  | non\_time\_series | `TagNonTimeSeriesPipeline`（一次性）            |
| `global` scope + `time_series` type     | global            | `TagGlobalPipeline`（sentinel `__global__`） |
| `per_entity` scope + `time_series` type | per\_entity       | `TagEntityPipeline` / `TagSlicePipeline`   |

per\_entity 路由通过 BacktestEngine 执行，复用回测引擎的时间轴和并行能力。

## 数据库表

| 表                       | 用途                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `sys_tag_scenario`      | 标签场景元数据（名称、执行模式、时间范围等）                                                                |
| `sys_tag_definition`    | 标签定义（name、display\_name、description、scenario\_id）                                     |
| `sys_tag_value`         | 标签值（entity\_id、tag\_definition\_id、as\_of\_date、json\_value、可选 start\_date/end\_date） |
| `sys_tag_calc_progress` | 增量计算水位线（scenario\_id、entity\_id、last\_calculated\_end）                                |

### 更新模式

| 模式               | 行为                                |
| ---------------- | --------------------------------- |
| `incremental`    | 只计算上次进度之后的日期，利用 `prior_value` 热启动 |
| `refresh`        | 删除标签值和进度行后重新计算                    |
| `recompute=True` | 全量重建：删除值、定义、进度行                   |

## API

```python
tag = Tag()

# 发现
tag.refresh()
tag.list_ids(enabled_only=True)   # ["demo/market_cap_tier", ...]
tag.list_keys(enabled_only=True)   # ["market_cap_tier", ...]
tag.find("market_cap_tier")        # DiscoveredTagInfo

# 执行
tag.execute()                                     # 运行所有已启用标签
tag.execute(scenario_name="demo/market_cap_tier") # 运行单个
tag.execute(scenario_name="...", dry_run=True)    # 试运行不写库

# 内联设置执行
tag.execute(
    settings=custom_settings,
    tag_key="custom_tag",
)
```

## 数据流

```
userspace/settings.py + tag.py
  → DiscoveryService 发现场景
  → TagSettings 校验配置
  → Scenario.from_tag_settings 构建运行时对象
  → MetadataEnsureService 同步场景+定义到 DB
  → TagEntityListResolver 从 data.base 解析实体池
  → 按 data.base 路由到对应管道
  → TagContext 传递给 calculate_tag / on_calendar_asof
  → TagValueFlushService 批量写入 sys_tag_value
  → sys_tag_calc_progress 更新水位线
  → 性能报告保存到标签目录
```

## 与其他模块的关系

| 模块                   | 关系                                                      |
| -------------------- | ------------------------------------------------------- |
| **backtest\_engine** | per\_entity 标签通过 BE 的 entity\_based / slice\_based 模式执行 |
| **data\_contract**   | 通过 ContractIssuer 签发数据合约，加载 K 线、财务等数据                   |
| **data\_manager**    | 通过 `stock.tags` 服务读写标签值                                 |
| **strategy**         | 策略可通过 `ctx.data("tag")` 读取标签数据进行筛选                      |

