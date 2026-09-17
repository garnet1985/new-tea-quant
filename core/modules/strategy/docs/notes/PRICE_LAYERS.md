# 价格三层：qfq 信号 / hfq ROI / raw 成交

**状态：** 口径已锁定（2026-09-09）。数据层已给三层价；enumerate 止盈止损 / `weighted_roi` 已切 hfq；price_factor 已聚合枚举 hfq ROI；portfolio 平仓已按 `股数 × 买入 raw × hfq ROI` 记账。  
**取代：** [CORPORATE_ACTION_CASH_ACCOUNTS.md](../../core/CORPORATE_ACTION_CASH_ACCOUNTS.md)（分红送转双账户 + Tushare `dividend` 不再做）。  
**三层共用：** enumerate / price_factor / portfolio 同一套尺，禁止一层 qfq、一层 raw 冻股数。

用户要的是：花 1000 买、最后值 1500 → ROI **50%**。不关心中间送转还是分红，不能把 0% 算成腰斩。

---

## 1. 三层各干什么

| 干什么 | 用什么 | 不要用 |
|---|---|---|
| 扫描、触发、形态、均线 | **qfq** | 不要用 qfq 当收益 |
| 比例止盈止损、`weighted_roi`、盈亏 | **hfq** | 不要用会穿零的 qfq 价做 `(出−入)/入` |
| 能买多少股、扣多少现金 | **买入 raw** | 不要用 hfq/qfq 当成交价去算股数 |

持股按**买入那一笔股数**不变。送转、分红都折进因子；变不变「真实流通股数」回测不展示、不参与盈亏。

```text
ROI     = (卖出 hfq − 买入 hfq) / 买入 hfq
盈利    = 买入股数 × 买入 raw × ROI
等价卖出价 = 买入 raw × (1 + ROI)    # 仅同股口径；不是交易所 raw 打印价
```

10 送 10：hfq 的 ROI 为 0，盈利为 0。`等价卖出价` 仍是 10 元量级，不是除权后的 5 元。回测不 care 那根 5 元。用送转后的股数再乘等价价会算两遍。

有 `exit_price_raw` 时，资金层用上面公式算钱即可，**禁止**再用 ROI 造一根「成交卖出价」。旧 bug 是 `买入 raw × (1 + qfq_ROI)`：qfq 穿零会得到负卖出价。换成 hfq 后，这条倒推只在「同股等价价」意义上成立，仍不要当成 raw 成交。

---

## 2. 外部依赖：只要复权因子

**不接** Tushare `dividend`，不拆分红 / 送股 / 转增。

表里**没有单独的 hfq 列**，也不需要再爬一种因子。`sys_adj_factor_events.factor` 就是 Tushare `adj_factor` 的绝对 F：一套因子，前复权除以最新 F 并加 C，后复权只乘 F。

当时不用 Tushare 的是 **qfq 行情**（和腾讯差一截平移），不是这根 F。Handler 用腾讯 qfq 锚 `C`，F 链仍来自 Tushare。ROI **不要**去拉 Tushare `pro_bar(adjust=hfq)`，也不要加 `C`。

```text
hfq(t) = raw(t) × F(t)          # 已有 F，消费时算
qfq(t) = raw(t) × F(段)/F(最新) + C   # 信号；C 来自腾讯锚
```

数据层（已落地）：``load`` / ``load_qfq`` / ``load_qfq_split`` / ``load_batch`` 以及契约 ``stock.kline.*`` 一律给下面这行，**不必也不要**在 settings 里声明 ``adjust``。旧参数若还在会被丢掉，不切换序列。只要未复权请用 ``load_raw``。

行形状（字段名是 ``high`` / ``low``，不是 highest/lowest；**没有**嵌套 ``qfq``，顶层就是前复权）：

```text
{
  date, id, term, volume, amount, …   # 非价格字段仍在顶层
  open, high, low, close, pre_close,  # = qfq；信号 / MA 读这里
  raw:  { open, high, low, close, pre_close },          # 成交股数、扣现金
  hfq:  { open, high, low, close, pre_close },          # raw × F；ROI / 比例止盈止损
  adj_factor: F                                         # 当日生效因子；无事件为 1
}
```

消费：``bar["close"]`` 信号；``bar["raw"]["close"]`` 成交；``bar["hfq"]["close"]`` 收益。``hfq.close = raw.close * adj_factor``，load 时已算好。

若必须让 ROI 涨跌和腾讯图逐点一致，才另接腾讯 `adjust=hfq` 当第二条 SOT（成本与 `qfq_anchor` 同类）。默认不做。

---

## 3. 因子里的分红 = 再投资

因子不单独记现金，当成除息日用红利买回同一只股票。相对「红利进账户、不再投入这只股」：

```text
差额 ≈ 分红占本金比例 × 除息后到卖出的涨跌幅
```

后来涨 → 略乐观；后来跌 → 略悲观；刚除息就卖 ≈ 0。

量级（公开市场统计，不是库内精确分位）：多数一次除息占股价 1%～3%；分红公司全年股息率大约九成在 ~4% 附近；全市场更低。极端如中国神华 2016 特别息约 18% 一次。普通持仓（周～月）再投资偏差通常是零点几个点，不是 10 送 10 那种假亏损。

配股若已打进 Tushare 因子，按供应商「全额认购」口径吃掉，不另建模。增发 / 转股一般不改变你的持股，raw 价里的稀释已经在；不必为它们加表。缩股若在因子里，hfq 会带上。

---

## 4. 现状（不要回退的部分）

已落地、仍有效：

- 资金买卖：买入扣 `entry_price_raw × 股数`；平仓盈利 = `股数 × 买入 raw × hfq ROI`（费用另扣）
- 资金日频盯市：`mark_px = entry_raw × (1 + (hfq_close − entry_hfq) / entry_hfq)`，不是 raw 收盘 × 冻结股数（10 送 10 会假腰斩）
- 代码：`portfolio/data_class/event.py`、`trade.py`、`simulator.py`、`report_manager/daily_mtm.py`
- 枚举 `_apply_exit` / 比例止盈止损 / 峰谷 / `weighted_roi` 用 hfq；产物带 `*_hfq`
- price_factor 无顺延吃枚举 `weighted_roi`；跌停顺延用 bar `hfq` 对 `entry_price_hfq` 重算；`roi × enter_hfq` 记均利（不是资金层现金）

算术只许 [`hfq_roi`](../../core/engines/shared/services/hfq_roi/hfq_roi.py)：`hfq_roi` / `hfq_target_hit` / `cash_profit` / `mark_value`。枚举成交与止盈止损、price_factor 顺延、portfolio 盯市与 `Trade`、决策者 holdings 都调它。记录的百分比用 `hfq_roi`；是否触达档位用 `hfq_target_hit`（价格比较，避免 `8/10−1` 浮点漏档）。手续费另扣，不进 ROI 分母。禁止 `(qfq 收盘 − raw 买价) / raw 买价`。

---

## 5. 落地时三层对齐

1. **enumerate：** 成交股数用 raw；止盈止损与 `weighted_roi` 用 hfq。胜负看 hfq ROI 符号。
2. **price_factor：** 继续聚合枚举的 `weighted_roi`，自己不要用 qfq 再算一遍收益。
3. **portfolio：** 买入 `entry_price_raw` × 买入股数扣现金；平仓盈利 = 买入股数 × 买入 raw × 该笔 hfq ROI（费用另扣）。日频盯市用同一把尺反推同股等价市值。不要第二种 ROI。

缺合法买入 raw 的笔不进资金层。hfq 分母须 `> 0`（后复权应满足；不满足则该笔不算收益）。

---

## 6. 明确不做

- 接 `dividend` 做双账户（送转改股数 + 现金红利）
- qfq 与 hfq 百分比填进同一列 `weighted_roi`
- 用 hfq 当买入价计算可买股数
- 未复权股数 × 交易所 raw 收盘去盯市（另见 [DAILY_MTM_RISK_RATIOS.md](../../core/engines/portfolio/docs/DAILY_MTM_RISK_RATIOS.md)）
