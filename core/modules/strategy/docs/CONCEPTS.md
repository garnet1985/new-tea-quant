# Strategy — 概念与运作

**模块：** `modules.strategy` · **版本：** `0.10.0`

本文写归因怎么运转：一套「如果」副本、三层懒执行、报告回答什么。目录与数据流见 [ARCHITECTURE.md](./ARCHITECTURE.md)；为什么这样定见 [DESIGN.md](./DESIGN.md)。

文字入口见 [README.md](../README.md)；调用见 [API.md](../API.md)；指纹与 version 见 [VERSIONING.md](./VERSIONING.md)。

---

## 归因在问什么

改一个设置，结果变好还是变坏、该设成多少。默认是单因素多档：其余保持当前 settings，只动一个轴，看该层曲线和敏感度排名。

三层问的不是同一件事：

| CLI | 须先有 | 补到 | 这一层回答 |
|-----|--------|------|------------|
| `sea` | `se` | 枚举 | 机会多不多、散不散；纸面止盈 / 止损 / 过期是否极端。含重叠，不是去噪账，也不是资金账 |
| `spa` | `sp` | 价格 | 去近邻之后，等权投一笔能不能赚、利润是否堆在少数笔。出场结构只描述，不代算盈利区间 |
| `soa` | `so` | 组合 | 钱有没有买到该买的；槽位、分配方式、资金怎么改变收益和回撤 |

平时 `Strategy.simulate` 只回测，不归因。决策模拟（人选谁、买多少）不进参数扫描。

---

## 一套副本，三次懒补

`attribution.py` 的顶层 `inputs` 展开成一套 version：当前主号是基准格，其余是副本 `{主号}-{r}`，不占主号序列。`sea` / `spa` / `soa` 共用这套身份。命令只决定补到哪一层、用哪一层指标画曲线。

只改价格去噪间隔时，枚举指纹可以与基准相同，价格层复用已有枚举。`sea` 展格时会丢掉只影响回放的近邻间隔，避免为同一枚举身份多跑一遍。

未写 `inputs` 时，系统按当前 effective 补一套默认轴（止损 / 止盈、可解析的 `core` 标量、可选的近邻间隔）。一旦写了非空 `inputs`，只扫声明的轴。

取值可以是列表，也可以是 `{"range": [起, 止], "step": 步长}`。读配置时展开，两端包含，步长为正，终点必须落在步长上。`None` 表示关掉该位置，和改数字一样会换执行指纹。省略的路径继承快照。`goal` 的一档是整段替换，不做字段级深合并。

`joint_sweep` 是额外的小矩阵：指定两三个已经声明的轴一起变，其余固定，报告里出热力图。全轴 `cross: true` 仍能把各轴做成笛卡尔积（上限 128 格），但报告仍按单因素讲，口径未定，不要当完成功能。开了全轴 `cross` 时忽略 `joint_sweep`。

滚动窗口写在同一份 `attribution.rolling.windows`，CLI `sw` 另跑，报告落在 `rolling/`，不和参数战役混在一张表里。产品口径未定。

配置不进执行指纹，也不进环境指纹。工作台保存 `settings.py` 时不要改 `attribution.py`。轴只写顶层 `inputs`。不要写 `versions`、`shap`、`overlays`、`matrix`，也不要把轴放进 `enum` / `price` / `portfolio` 块。

---

## 组合资金是另一轮

`soa` 上，资金分配不进上面那套共用 `inputs`。`allocation` 单独做单因素扫描：锚定当前主 version，复用已有枚举，只改分配再补组合。

可以扫的包括分配方式、持仓数、初始资金、单票上限、Kelly 系数、每笔手数、选仓排序。未写 `allocation` 时，按当前 settings 生成默认档。声明了 `allocation` 之后，单票上限、Kelly 系数、每笔手数不会再自动加进默认档，除非自己写上。

选仓排序在 `portfolio.allocation.opportunity_selection`。不写、空列表、或权重全是 0，都是到达顺序。写了 `on_pick_portfolio_member` 时仍以钩子为准。

---

## 报告长什么样

跑哪一层，就出那一层的报告。主产物是敏感度排名、每轴一条曲线、该层问题章节。有 `joint_sweep` 时再加一张热力表。

- 枚举章节看机会数量、覆盖、时间分散、纸面出场，以及止盈之后还有没有空间（一档全平时标明不可测）。
- 价格章节看去噪后的边、利润是否集中、哪种出场贡献了利润。
- 组合章节看折损、买到和漏掉、仓位结构。想法轴即使在共用副本上有组合产物，结论也不再讲成一遍因子贡献。

文案带条件：其余设置保持当前时，样本内哪一档较好。没有对照格就不编百分比。

归因组按环境指纹再加策略 version（`parent_version_id`）分开。策略换成新 version 后，上一版的报告不再当作当前这份；回到那个 version，对应报告还在。

---

## 现场量

要扫的阈值在 settings 里，一次回测内是常数，不需要再 `capture`。机会成立当时的读数来自 as-of 当日那一片 `signal_snapshot`；钩子自己算的、未声明的量用 `capture`，同名以用户为准。已经跑完、快照里没有这些列的旧 version，补不出当日读数。

---

## 相关文档

- [README](../README.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [架构](./ARCHITECTURE.md)
- [设计](./DESIGN.md)
- [Version / 指纹](./VERSIONING.md)
- [价格回放](./notes/PRICE_REPLAY.md)
- [选仓排序](./notes/OPPORTUNITY_SELECTION.md)
