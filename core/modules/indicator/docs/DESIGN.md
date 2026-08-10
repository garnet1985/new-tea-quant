# Indicator 设计说明

**版本：** `0.3.0`

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## K 线字段

**`calculate`** 使用的 **`_klines_to_dataframe`** 要求存在列：**`open`**、**`high`**、**`low`**、**`close`**。可选 **`volume`**。

调用方传入的价格字段含义由上游决定（例如 DataManager 的前复权 / 未复权 K 线）；本模块不做复权。

---

## `compute` 分层

策略配置路径优先走 **`compute` / `compute_batch`**：

1. **close 序列**：`rsi` 与 `_CLOSE_SERIES_INDICATORS`（如 `sma` / `ema`）
2. **裁剪 OHLCV**：便捷方法与 `_OHLCV_DIRECT_INDICATORS`（去掉无关列）
3. **宽表 `calculate`**：其余未知指标名回退完整行 → DataFrame

**`calculate`** 始终走完整 OHLCV 宽表，适合通用 / 探索调用。

---

## `calculate` 调用约定

对 **`cls._ta`** 上 **`indicator_name`** 指到的可调用对象，传入关键字参数：

- **`high` / `low` / `close` / `open_`**：来自 DataFrame（**`open_`** 因 pandas-ta 参数名）。
- **`volume`**：`df.get('volume')`，可能为 `None`。
- 其余 **`**params`** 原样透传（如 **`length`**、**`fast`**）。

若库函数签名与上述不兼容，需在业务侧换用其它指标名或自行封装。

---

## RSI 特例

**`rsi`** 不经过完整 OHLC DataFrame 管线：仅用 **`close`** 序列构造 **`pd.Series`** 再调 **`_ta.rsi`**，便于仅有收盘价的数据源。

---

## 返回值

- **单列**：`List[float]`（含前导 `NaN` 与库一致，调用方按需截断）。
- **多列**：`Dict[str, List[float]]`，键名为 pandas-ta 生成的列名（如 MACD、布林带）。

---

## 策略配置对齐

**[AVAILABLE_INDICATORS.md](./AVAILABLE_INDICATORS.md)** 描述 **`settings.data.indicators`** 中指标名与 **`compute(..., **params)`** 的对应关系；新增便捷方法时在 **`core/indicator.py`** 增加 **`@classmethod`** 包装即可。

---

## pandas-ta `verify_series` monkeypatch

加载 TA 库时，**`_patch_pandas_ta_verify_series`** 会替换 `pandas_ta_classic.utils._core.verify_series`：

- 数据行数不足时不再刷屏式英文告警，改为本模块 **DEBUG** 中文日志并返回 `None`。
- 补丁带 `_tea_patched` 标记，进程内只打一次。
- **不改变**「不足长度则跳过计算」的语义，只收口日志噪音。

---

## 相关文档

- [API.md](../API.md)

---

## 设计决策（原 DECISIONS.md）

# Indicator 设计决策

**版本：** `0.3.0`

---

## 决策 1：代理 pandas-ta-classic，不自研公式

**背景（Context）**  
指标数量多、维护成本高。

**决策（Decision）**  
以 **`pandas-ta-classic`** 为唯一实现源，**`Indicator`** 只做转换与调用。

**理由（Rationale）**  
与社区实现一致，减少数值偏差争议。

**影响（Consequences）**  
库版本升级可能带来列名或默认参数变化，需在升级后回归测试。

---

## 决策 2：静态服务类、无缓存

**背景（Context）**  
不同调用方对窗口与参数组合需求差异大。

**决策（Decision）**  
**不**在模块内缓存计算结果；每次调用重新算。

**理由（Rationale）**  
避免错误共享与内存占用不可控；需要缓存时在 Strategy/Tag 层做。

**影响（Consequences）**  
高频重复计算需调用方优化。

---

## 决策 3：错误返回 None

**背景（Context）**  
指标失败不应拖垮整条扫描链路。

**决策（Decision）**  
捕获异常、打日志，返回 **`None`**。

**理由（Rationale）**  
与现有调用方习惯一致（见 `calculate` 实现）。

**影响（Consequences）**  
调用方必须判空。

---

## 决策 4：RSI 仅依赖 close

**背景（Context）**  
部分数据只有收盘价序列。

**决策（Decision）**  
**`rsi`** 单独路径，不强制完整 OHLC DataFrame。

**理由（Rationale）**  
提高可用性，避免无意义的 `high/low` 依赖。

**影响（Consequences）**  
与 **`calculate('rsi', ...)`** 行为需保持 mentally一致（均基于 close）。

---

## 决策 5：进程内延迟加载 + verify_series 补丁

**背景（Context）**  
首次导入 TA 库成本高；默认不足长度告警在批量扫描时噪音大。

**决策（Decision）**  
`_init_ta` 短路缓存模块对象；加载时打一次性中文 DEBUG monkeypatch。

**理由（Rationale）**  
预热可控、日志可读，且不改变跳过语义。

**影响（Consequences）**  
依赖 pandas-ta 内部 `utils._core` 路径；库大改版时需回归补丁。
