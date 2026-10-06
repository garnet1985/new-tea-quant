# 组合选仓排序

**状态：** 已实施（2026-10-06）。设置在 ``portfolio.allocation.opportunity_selection``；选仓在 ``OpportunityRanker``。

**一句话：** 当天机会多于剩余槽位时，用 `opportunity_selection` 声明排序或打分，再取前 N 个。未写钩子时走这份配置；写了 `on_pick_portfolio_member` 时仍以钩子为准。

---

## 1. 要补的缺口

`EntrySelector` 现在按机会到达顺序填满剩余槽位（`max_portfolio_size` 减去已持有）。20 个机会、只剩 5 个槽时，留下谁完全取决于到达顺序。用户若要按收盘价、PE、GDP 来挑，只能自己实现 `on_pick_portfolio_member`。

本配置放在组合设置里，和槽位、分配方式一起生效。它不进 `attribution.py`。归因以后若要对照不同排序，再单独加轴。

---

## 2. 配置位置与形状

`settings.portfolio.allocation.opportunity_selection`，列表。缺省或 `[]`：保持现在的到达顺序。

每一项是一个字段，外加可选的 `src`。同一项里不要写两个字段。

同一份列表只能是一种模式：

- 值全是 `"ASC"` / `"DESC"`：多关键字排序。
- 值全是数字（可负）：加权打分。

两种混在同一列表里，设置校验失败。

### 2.1 多关键字排序

按书写顺序排序，后面的字段只在前面打平时生效。然后取前 N 个。

```python
"opportunity_selection": [
    {"close": "DESC"},
    {"pe": "ASC"},
]
```

先按收盘价从高到低，收盘价相同再按 PE 从低到高。

### 2.2 加权打分

先在**当天仍可买的机会**里，把每个字段归一化到 0–1，再按权重加总，分数高的在前。

```python
"opportunity_selection": [
    {"close": 20},
    {"pe": 80},
]
```

收盘价占 20%，PE 占 80%。正权重表示数值越大越优先。

数值越小越优先时用负权重。低 PE 优先：

```python
"opportunity_selection": [
    {"close": 20},
    {"pe": -80},
]
```

权重按绝对值占比例。上例收盘价贡献 `0.2 * norm(close)`，PE 贡献 `-0.8 * norm(pe)`。PE 越高，这一项越负，总排名越靠后。

---

## 3. 字段从哪读

读机会上的 `signal_snapshot`。这是触发当时的一片现场，选仓用的 `to_opportunity()` 会原样带上。里面没有后来的涨跌结果。

写入规则（已有，`AsOfSnapshot`）：

- 主数据（一般是日 K）最后一根的数字字段，不带前缀。K 线收盘价就是 `close`。`date`、`raw`、`hfq` 不收。
- `settings.data.required` 里的其他数据源，各取截止当天的最后一行，只收数字，键名是 `数据源.字段`。例如 `gdp.close`、`stock.finance.quarterly.netprofit`。
- `has_opportunity` 里 `capture` 的同名键覆盖自动快照。
- 未声明的数据源、整段历史、非数字字段、策略参数（阈值、止损）不在这片快照里。

同名不会互相覆盖：K 线的 `close` 与 GDP 的 `close` 在快照里是 `close` 和 `gdp.close`。

### 3.1 `src`

`src` 写成该数据源在 `settings.data` 里的 `data_key`。

| 写法 | 读到的快照键 |
|------|----------------|
| `{"close": 20}` 或不写 `src` | `close`（主数据） |
| `{"close": 20, "src": "stock.kline.daily"}` 且这是主数据 | `close` |
| `{"close": 80, "src": "gdp"}` | `gdp.close` |

`"ASC"` / `"DESC"` 同样可以带 `src`：

```python
"opportunity_selection": [
    {"close": 20, "src": "stock.kline.daily"},
    {"close": 80, "src": "gdp"},
]
```

---

## 4. 当天怎么选

在 `EnterSelection.select_for_date` 里，钩子未 override 时：

1. 当天可买机会里，去掉实体已经在持仓中的。
2. 按第 2 节排序或打分。分数或排序键打平的，保持原来的到达顺序。
3. 把排好的列表交给现有 `EntrySelector.pick`：同一天同一只股票只留更靠前的那一笔，取满剩余槽位为止。

N 就是剩余槽位（`max_portfolio_size` 减去已持有），不在配置里另写一个 N。

归一化只在第 1 步剩下的这批机会上做，不跨天、不拿全历史。

- 有值的机会：`(x - min) / (max - min)`，min/max 来自当天这批里该键有值的机会。
- 该键当天全体相同，或只有一个有值：这一项记 0。
- 某个机会缺这个键：这一项记 0，排在有值的后面（排序模式下缺键沉底）。不因此丢掉它的槽位资格。
- 运行时键不存在不让回测失败。

钩子 override 了 `on_pick_portfolio_member` 时，不读这份配置。

---

## 5. 校验

加载 settings 时：

- 必须是 list；每一项是 dict。
- 每一项恰好一个字段名，可选 `src`。`src` 若写了必须是非空字符串。
- 字段名不能是 `src`。
- 全部值为 `ASC` / `DESC`（大小写不敏感，存成大写），或全部为数字，不能混用。
- 权重至少有一个非 0。全 0 视为未配置排序。

不在加载时要求 `src` 一定出现在 `data.required` 里。快照里没有的键按第 4 节记 0 / 沉底。

---

## 6. 实施时改哪里

- `portfolio_settings.py`：解析、默认（缺省等于不排序）、校验。
- `EnterSelection.select_for_date`：钩子未 override 时，先按配置重排 `available`，再 `pick_ids`。
- 排序与归一化放在选仓旁的小模块，不放进 `AllocationStrategy`（那是算买多少）。
- 单测：多关键字顺序、负权重、同名字段加 `src`、缺键沉底、已持仓不参与、同股留更靠前者、钩子 override 时忽略配置。

本次不改 `AsOfSnapshot` 的键名，也不把这份配置放进归因展格。
