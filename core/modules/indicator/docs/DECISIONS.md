# Indicator — 设计与决策

**模块：** `modules.indicator` · **版本：** `0.2.1`

**最低支持核心版本：** `>=0.5.0`

本文记录本模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

为策略与扫描链路提供技术指标计算能力：以 **`pandas-ta-classic`** 为唯一实现源，本模块只做转换与调用，不自研公式。约束与上下文：

- **`calculate`** 使用的 **`_klines_to_dataframe`** 要求存在列：**`open`**、**`high`**、**`low`**、**`close`**，可选 **`volume`**；调用方传入的价格字段含义（前复权 / 未复权）由上游决定，本模块不做复权。
- 指标数量多、维护成本高，需要与社区实现保持一致，减少数值偏差争议。
- 指标失败不应拖垮整条扫描链路。
- 部分数据源只有收盘价序列。
- 首次导入 TA 库成本高；默认「不足长度」英文告警在批量扫描时噪音大。

## 方案与思路

**`compute` 分层**：策略配置路径优先走 **`compute` / `compute_batch`**：

1. **close 序列**：`rsi` 与 `_CLOSE_SERIES_INDICATORS`（如 `sma` / `ema`）
2. **裁剪 OHLCV**：便捷方法与 `_OHLCV_DIRECT_INDICATORS`（去掉无关列）
3. **宽表 `calculate`**：其余未知指标名回退完整行 → DataFrame

**`calculate`** 始终走完整 OHLCV 宽表，适合通用 / 探索调用。

**`calculate` 调用约定**：对 **`cls._ta`** 上 **`indicator_name`** 指到的可调用对象传入关键字参数——**`high` / `low` / `close` / `open_`** 来自 DataFrame（**`open_`** 因 pandas-ta 参数名）；**`volume`** 取 `df.get('volume')`，可能为 `None`；其余 **`**params`** 原样透传（如 **`length`**、**`fast`**）。若库函数签名与上述不兼容，需在业务侧换用其它指标名或自行封装。

**RSI 特例**：**`rsi`** 不经过完整 OHLC DataFrame 管线，仅用 **`close`** 序列构造 **`pd.Series`** 再调 **`_ta.rsi`**，便于仅有收盘价的数据源（见下文 DEC-04）。

**返回值**：单列返回 `List[float]`（含前导 `NaN`，与库一致，调用方按需截断）；多列返回 `Dict[str, List[float]]`，键名为 pandas-ta 生成的列名（如 MACD、布林带）。

**策略配置对齐**：[AVAILABLE_INDICATORS.md](./AVAILABLE_INDICATORS.md) 描述 **`settings.data.indicators`** 中指标名与 **`compute(..., **params)`** 的对应关系；新增便捷方法时在 **`core/indicator.py`** 增加 **`@classmethod`** 包装即可。

**pandas-ta `verify_series` monkeypatch**：加载 TA 库时，**`_patch_pandas_ta_verify_series`** 替换 `pandas_ta_classic.utils._core.verify_series`：数据行数不足时不再刷屏式英文告警，改为本模块 **DEBUG** 中文日志并返回 `None`；补丁带 `_tea_patched` 标记，进程内只打一次；**不改变**「不足长度则跳过计算」的语义，只收口日志噪音（见下文 DEC-05）。

---

## DEC-01：决策 1：代理 pandas-ta-classic，不自研公式

**背景（Context）**  
指标数量多、维护成本高。

**决策（Decision）**  
以 **`pandas-ta-classic`** 为唯一实现源，**`Indicator`** 只做转换与调用。

**理由（Rationale）**  
与社区实现一致，减少数值偏差争议。

**影响（Consequences）**  
库版本升级可能带来列名或默认参数变化，需在升级后回归测试。

---

## DEC-02：决策 2：静态服务类、无缓存

**背景（Context）**  
不同调用方对窗口与参数组合需求差异大。

**决策（Decision）**  
**不**在模块内缓存计算结果；每次调用重新算。

**理由（Rationale）**  
避免错误共享与内存占用不可控；需要缓存时在 Strategy/Tag 层做。

**影响（Consequences）**  
高频重复计算需调用方优化。

---

## DEC-03：决策 3：错误返回 None

**背景（Context）**  
指标失败不应拖垮整条扫描链路。

**决策（Decision）**  
捕获异常、打日志，返回 **`None`**。

**理由（Rationale）**  
与现有调用方习惯一致（见 `calculate` 实现）。

**影响（Consequences）**  
调用方必须判空。

---

## DEC-04：决策 4：RSI 仅依赖 close

**背景（Context）**  
部分数据只有收盘价序列。

**决策（Decision）**  
**`rsi`** 单独路径，不强制完整 OHLC DataFrame。

**理由（Rationale）**  
提高可用性，避免无意义的 `high/low` 依赖。

**影响（Consequences）**  
与 **`calculate('rsi', ...)`** 行为需保持 mentally一致（均基于 close）。

---

## DEC-05：决策 5：进程内延迟加载 + verify_series 补丁

**背景（Context）**  
首次导入 TA 库成本高；默认不足长度告警在批量扫描时噪音大。

**决策（Decision）**  
`_init_ta` 短路缓存模块对象；加载时打一次性中文 DEBUG monkeypatch。

**理由（Rationale）**  
预热可控、日志可读，且不改变跳过语义。

**影响（Consequences）**  
依赖 pandas-ta 内部 `utils._core` 路径；库大改版时需回归补丁。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
