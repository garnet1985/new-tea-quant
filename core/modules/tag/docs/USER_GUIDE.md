# Tag — 用户指南

**版本：** `0.4.1`

`Tag 批量算因子并存到数据库——每日全市场跑一遍 PE、PB、换手率，策略回测时直接查表用。`  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 自动发现 `userspace/extensions/tags/` 下的因子场景，列出可以跑哪些
- 跑"打标"：把一只股 / 一个时点的因子值算出来，落进数据库
- 支持增量续算——从每只股上次算到的日期往后接着跑，不用每次从头算
- 支持三种计算方式：按股票逐只算（如 PE、换手率）、按整个市场算（如宏观口径）、非时序一次性批量算（如地域归类）
- 策略只要在 `settings.py` 里声明引用，就能直接查到这些因子值，不用自己再算一遍

## 配置说明

因子场景的用户可配项都在 `userspace/extensions/tags/<你的场景>/settings.py`。下面是最常调的几组字段（全字段说明见 `userspace/extensions/tags/settings_example.py`）：

| 配项 | 在哪配 | 默认值 | 说明 |
|------|--------|--------|------|
| `is_enabled` | settings.py 根级 | `False` | 是否被框架发现；忘了开 CLI 列表里看不到 |
| `meta.key` | settings.py `meta` | 必填 | CLI `--scenario` 用的短名，全局唯一 |
| `core` | settings.py `core` | `{}` | 场景私有参数（阈值、映射表等），键名自定 |
| `calculation.update_mode` | settings.py `calculation` | `incremental` | `incremental`=从上次进度续算；`refresh`=指定区间重算 |
| `calculation.recompute` | settings.py `calculation` | `False` | 一次性运维开关，本次跑等价 refresh |
| `calculation.is_dry_run` | settings.py `calculation` | `False` | 只算不落库，试算用 |
| `calculation.execution.start_date` / `end_date` | settings.py `calculation.execution` | 空=全量范围 | 计算区间（YYYYMMDD） |
| `calculation.execution.mode` | settings.py `calculation.execution` | `entity_based` | 仅"按股票逐只算"场景生效；`entity_based` 或 `slice_based` |
| `data.base.data_key` | settings.py `data.base` | 必填 | 主数据（日 K / 周 K / 宏观 / 股票列表），决定走哪种计算方式 |
| `data.required` | settings.py `data` | `[]` | 额外要注入的数据（板块指标、其它宏观等） |
| `data.min_required_records` | settings.py `data` | `0` | 触发因子前至少需要多少根历史记录（warmup） |
| `tag_definitions` | settings.py 根级 | 必填 | 列出本场景会打上哪些标签，至少 1 条 |

## 常见使用方式

### 场景 1：每日定时刷新一批因子

1. 先拉数据：`python cli.py r`，把 K 线、财报等更到最新。
2. 跑所有启用的场景：`python cli.py t`；只想跑某一个就加 `--scenario 短名`。
3. 默认走 `incremental`，从每只股上次算到的日期往后接着算，已算过的部分不重跑。
4. 想每天定时刷一次，把这条命令挂到系统计划任务（cron / 任务计划程序）里即可。

### 场景 2：在策略里引用一个因子

1. 打开策略的 `settings.py`。
2. 在 `data.required` 里加一条：`{"data_key": "tag", "params": {"tag_scenario": "场景短名"}}`。
3. 策略代码里跟读普通字段一样取因子值（来自当日注入的记录）。
4. 前提是这个因子已经跑过、库里有值——否则会读到空。

### 场景 3：手动重算某段时间的因子

1. 打开场景的 `settings.py`。
2. 把 `calculation.execution.start_date` / `end_date` 设成想重算的区间。
3. 把 `calculation.update_mode` 改成 `refresh`（或者临时把 `recompute` 设为 `True`）。
4. 跑 `python cli.py t --scenario 场景短名`。
5. 跑完记得把 `recompute` 改回 `False`、把区间恢复，避免下次又重算。

### 场景 4：先试算看看，不落库

1. 把 `calculation.is_dry_run` 设为 `True`。
2. 跑 `python cli.py t --scenario 场景短名`。
3. 终端会打印将要打上的标签和值，但不写数据库、也不推进进度水位。
4. 验证逻辑没问题后关掉 dry_run 再真跑一遍。

## 常见坑与注意事项

- **改了因子代码，策略里读到的还是旧值：** Tag 默认走 `incremental`，只续算新数据，不会回头重算历史。改了 `tag.py` 的计算逻辑后，要用 `refresh`（或 `recompute: True`）把目标区间重算一遍。
- **算出来全是空 / NaN：** 最常见是底层数据还没抓到对应区间，先跑 `python cli.py r` 更新；其次检查 `data.min_required_records` 是不是太小（warmup 不足也算不出有效值）。
- **CLI 找不到场景：** 用 `python cli.py ls tags` 看实际被发现的场景和短名；依次检查 `is_enabled: True`、目录不在 `_` 开头路径下、`meta.key` 全局唯一。
- **"按股票逐只算"场景忘了写 `execution.mode`：** 这类场景需要显式声明 `entity_based` 或 `slice_based`；横截面逻辑必须在 `slice_based` 下才能跑通。
- **value 里塞了分类信息：** 一个标签的 value 只放"当时的注解"（数量、明细），分类名写在 `tag_definitions` 的 `display_name` 里，别塞进 value。

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
