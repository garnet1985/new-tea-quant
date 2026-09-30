# 矩阵归因（战役）

**状态：** 口径已锁定（2026-09-30）。本轮只记下方案，并去掉「每次 simulate 顺带归因」。战役入口、group 索引、自动 as-of 快照 **尚未落地**。  
**一句话：** 平时 Run 只验证这一份想法；归因是事后对照，由 `engines/analyzer` 驱动一份 matrix，复用已有 version 缓存。  
**位置：** 业务在 `strategy/engines/analyzer`；统计原语仍在 `modules.analysis`。不新开 `factor` 模块，也不把调度并进 `modules.analysis`。

---

## 1. 为什么去掉单次归因

一次 Run 里 settings 旋钮是常数。对「把止盈从 20% 改成 30%，账户变好了没有」这个问题，单次回测内部的共变回答不了，报告看起来会像在玩。

单次还能看的，只剩另一问：在这套已经定死的参数下，各笔机会当时的 RSI / MACD 和这笔盈亏有没有一起动。这是交易层面的探查，不是参数归因。不要再和战役叫成同一件事，也不要挂在每次 `simulate` 上。

因此：

- 删除 `settings.analysis.enabled`
- `Strategy.simulate` 不再调用 `Analyzer.run`
- 不再提供 CLI `sa` / 工作台逐步归因区块

`Analyzer.run` 以及 prepare / analyze / report 流水线作为 **库** 留下，给之后的战役入口用。

---

## 2. 默认 Run 是什么

默认跑策略 = 验证这一次的想法：一个 `settings.py`、一个 version。不自动开多版本，不自动归因。

专门要归因时再开独立入口。它先读已经留下的号；只有用户明确要补格子、而且现有号盖不住时，才额外调用 `Strategy.simulate`。那是这一次战役自己的事，不改变平时 Run 的含义。

strategy 仍然是「把一个想法跑完」。归因是事后对照，不是因子挖掘器。全市场因子研究（IC / 滚动 / 离开某一条策略）留给以后的 `factor` 产品线。

---

## 3. Group ≠ 可以归因

这两个词不要混用。

**Group（归档）**  
键是 `env_fp`。代码、NTQ 版本、库类型、data contract 没变，跑过的 version 都记进去。一年、三年、滚动窗里的每一段，只要环境没变，都进这一组。组是「这部策略在这个环境下跑过哪些号」，不是「可以倒进同一张回归表」。

`group_meta` 里再按样本窗做一层索引：区间 + 股票池 → 这批 version。

同一对 `(execute_fp, env_fp)` 命中旧号时不要重复记。

**可以归因（某一次任务的样本）**  
参数 matrix 只收与这次快照 **区间、股票池相同** 的号，真正不同的只有 matrix 里声明的旋钮取值。`core` 字段改名、钩子源码改了 → `env_fp` 变 → 新 group，旧命名空间停在旧组。

同组只说明「还是那套策略环境」。进不进这一张表，看这次任务锁的是哪一种样本。

不要把日期塞进 `env_fp`。区间改得回去，不属于环境。也不要为归因再加第三种指纹；两枚已经够圈出「同环境、同一样本、只改旋钮」。

---

## 4. 三种任务（后两种可后做）

| 任务 | 锁什么 | 动什么 | 不要做的 |
|------|--------|--------|----------|
| **参数归因（matrix）** | 这次快照的区间和股票池 | `core` / `goal` 等声明旋钮 | 把一年和三年当成同一列的两个取值 |
| **滚动验证** | 旋钮（或很少几组完整设置） | 声明好的窗口 | 和参数矩阵混在一份报告里 |
| **单次内部切片** | 这一版已留下的 snapshot | 现场 RSI 等与单笔盈亏 | 每次回测默认跑；不要叫成战役 |

产物可以仍写在同一个 `results/attribution/{group}/` 下，**任务类型分开**。

决策模拟不进自动扫描：那一层改的是人选谁、买多少，不是设置旋钮。

---

## 5. 流程

平时 Run 只多写一行组成员（落地时），不额外跑回测。

归因是单独入口。点名方式见 [§10](#10-attributionpy)。用当前 `settings.py` 的 effective 当快照，matrix 每一行是一格 overlay：

```text
读当前 settings 快照 + attribution.py
  → versions 非空则选号；否则按 matrix 每一行 overlay 成一格
  → 算 execute_fp，在 group 里找缓存
  → 命中则直接读该 {vid}/
  → 不命中且 fill_missing 再 Strategy.simulate
  → 拼表交给 modules.analysis
```

配置是策略旁的 `attribution.py`，不是 `settings.analysis` 开关，不进指纹。

磁盘：

```text
{strategy}/results/attribution/{group_id}/
  group_meta.json
  {task_id}/          # 参数归因与滚动验证分开
```

每个 version 仍各写各的 `{vid}/`。enum / price / portfolio 继续共享这个号。一次战役、一份报告，里面三栏（用户可以只扫到某一层来省时间，报告结构不变）：

- 枚举：机会够不够、密不密
- 价格：单笔赚不赚
- 资金层（最接近账户）：收益、回撤、利用率

扫描开始时给这批 registry 行记同一个 cohort / group id。清理规则要认这个 id：这一批要么一起留，要么一起删，不能按「最旧的未固定版本」拆开。战役用的 version 需要显式留下来。

---

## 6. 指纹怎么用

不改身份规则，不把设置指纹升成父级。缺的是「这几号是同一批」的索引。

| 指纹 | 里面有什么 | 归因怎么用 |
|------|------------|------------|
| `env_fp` | 策略路径、NTQ 版本、DB 类型、hooks 源码、data contract 映射文件哈希 | group 键 |
| `execute_fp` | 白名单 settings（含 `simulation` 区间）+ 排序后的股票池 | 用「快照 + 一格 matrix」算目标指纹，在 group 里命中 |

`meta` / `is_enabled` / `scanner` 等本来就不进 `execute_fp`。

指纹锁不住的是库里的行情内容：合约映射文件没变、K 线却被重新导入时，同一对指纹仍会命中旧 version。第一期当作已知限制，不为此再拆一枚指纹。

---

## 7. 两类可解释量：自动 vs `capture`

归因都该收，但来源不同。

| 你要解释的 | 自动？ | 从哪来 |
|------------|--------|--------|
| 阈值扫 20 / 25 / 30 账户怎么变 | 是 | 各 version 的 `effective_settings.json`（matrix 路径） |
| 这笔买入时 RSI / MACD 是多少 | `settings.data` 声明了该列则是；否则要 `capture` | 该笔 as-of snapshot |
| 钩子里自己算的、未声明的量 | 否 | 必须 `capture` |

**设置参数**不需要、也不应该再 `capture` 一遍。它们在单次运行里是常数，写进 snapshot 没有新信息。matrix 任务只读 matrix 里写的设置路径。旋钮写死在 `strategy.py`、不在 settings 中，现有产物里没有这个值，matrix 也扫不到；要参与归因，就把它放进 settings。

**实时指标**（机会 A 的 RSI 是 17、机会 B 是 19）不在 settings 里。正确做法不是寄希望于用户记得 `capture`：

- 机会成立的那一根，留下 **as-of 当日那一片**：base 那根 K 线（含已声明指标列），再加上当时其它已声明数据的最后一行
- 用户 `capture` 合并进去，同名以用户为准
- 不要整段历史，也不要事后再去行情库里猜

这只对之后的 Run 生效。已经跑完、snapshot 里没有这些列的旧 version，补不出当日读数。

当前代码还没做完自动快照：命中时当日 bar 已在 `Opportunity.record_of_today`，落盘时被丢掉，归因又只读 `signal_snapshot`（来自 `ctx.take_captures()`）。所以 `rsi_v1` 才手写 `capture("rsi", rsi)`。`rsi_length` / 阈值那种 capture 是多余的。

---

## 8. 模块边界

```text
战役入口（analyzer，待做）
  → strategy（group 索引 / 拼表 / 复用 Strategy.simulate）
  → modules.analysis（分桶、相关、对照；无业务、无 I/O）
```

- **不要**并进 `modules.analysis`：它不能调度、不能读盘、不能开 N 次回测
- **不要**再开一个和 strategy 平级的 `modules.attribution`：group、指纹、version 缓存、枚举落盘都已经在 strategy；拆出去只会再实现一遍
- **不要**做成四层后面的第五层回测：扫描是旁边一种跑法，每个 version 仍按原来的层往下跑
- **不要**把这次扫描塞回「跑一次回测顺便归因」的开关

`Analyzer` 继续担任归因的职责：现在是单 version 的 prepare → analyze → report 库；战役落地后由它读 group / 展开 matrix / 调 analysis。

---

## 9. 本轮明确不做

- 战役 CLI / BFF / UI 入口
- Run 时写 `results/attribution/{group}/group_meta.json`
- 机会成立时自动写入 as-of 当日那一片
- 滚动验证任务
- 把 `capture` 改成只收自定义量（示例策略可后清）

---

## 10. `attribution.py`

单独文件，与 `settings.py` 并列。Workbench 保存 settings 时不要改它。不进 `execute_fp` / `env_fp`。

没有 `mode`：`versions` 非空就是选号；没有或 `[]` 就走 `matrix`。两者都空则非法。不提供「空 versions = 当前窗口全选」。

```python
attribution = {
    "steps": ["enumerate", "price_factor", "portfolio"],
    "fill_missing": False,
    # "versions": [3, 5, 7],
    "matrix": [
        {
            "core": {"rsi_oversold_threshold": 20},
            "goal": {
                "stop_loss": {
                    "stages": [{"ratio": -0.1, "close_invest": True}],
                }
            },
        },
        {
            "core": {"rsi_oversold_threshold": 25},
            "goal": {
                "stop_loss": {
                    "stages": [{"ratio": -0.2, "close_invest": True}],
                }
            },
        },
        {
            "core": {"rsi_oversold_threshold": 30},
            "goal": {
                "stop_loss": {
                    "stages": [{"ratio": -0.3, "close_invest": True}],
                }
            },
        },
    ],
}
```

上例是 **3 格**（三套配套设置），不是 3×3。笛卡尔积不是语法；要交叉就自己写够行。

### Overlay

快照 = 当前 `settings.py` 抽出的 **effective**。每一格 = 快照 + 这一行 override → 再走一遍 `to_usable` / `extract_execute_settings`，和普通 Run 同一套身份。

- Overlay 只允许 `execute_fp` 白名单块。写 `meta` / `scanner` / `is_enabled` 报错。
- **一格声明一次要动的位置。** 没写到的兄弟键（只改 `stop_loss` 时的 `take_profit`）留在快照里。
- **动到 effective 的哪个位置，就换掉那个位置上的整份值**（该位置在 effective 里的全部字段）。不要字段级深合并：不能只写一档的 `ratio` 却继承同一档里的 `close_invest`。
- 独立旋钮（`core` 里各 key）各算各的位置，所以可以只 override `rsi_oversold_threshold`。
- **list 整段替换。** 写了 `stop_loss.stages` 就换整张 stages；每一档必须把 effective 里该种对象的字段写全。

`fill_missing` 默认 `False`。`kind: rolling` 不进这份文件。

相关现行契约：[VERSIONING.md](../VERSIONING.md)、[DECISIONS.md](../DECISIONS.md)、analyzer [BOUNDARY.md](../../core/engines/analyzer/docs/BOUNDARY.md)。
