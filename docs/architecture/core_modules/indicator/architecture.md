# Indicator 架构文档

**版本：** 1.0  
**最后更新：** 2026-01-XX

---

## 目录

1. [设计背景](#设计背景)
2. [设计目标](#设计目标)
3. [整体架构](#整体架构)
4. [核心组件与职责](#核心组件与职责)
5. [数据与调用流程](#数据与调用流程)
6. [API 设计](#api-设计)
7. [扩展与演进](#扩展与演进)
8. [相关文档](#相关文档)

---

## 设计背景

### 问题与痛点

在引入 `Indicator` 模块之前，技术指标计算存在以下问题：

1. **实现分散**：
   - 各个模块（Strategy、Tag、Analyzer）各自实现或直接调用第三方库
   - 指标名称、参数、返回格式不统一
2. **复用困难**：
   - 相同指标逻辑在不同模块中重复出现
   - 更新指标实现或修复 bug 时需要修改多处代码
3. **耦合第三方库细节**：
   - 业务代码直接依赖 `pandas-ta-classic` API
   - 更换指标库或升级版本成本高

### 业务需求

1. 为策略、标签、分析等模块提供**统一、稳定**的指标计算接口
2. 支持 **150+** 技术指标，覆盖趋势、动量、波动率、成交量等常见类别
3. 保留一定的灵活性：既有高频常用指标的便捷调用，也支持任意指标的通用调用

---

## 设计目标

1. **Proxy 而非重写**：
   - 完全复用 `pandas-ta-classic` 的指标实现，不复制算法代码
2. **单一入口**：
   - 所有指标计算通过 `IndicatorService` 访问
3. **统一数据格式**：
   - 统一输入 / 输出格式，屏蔽 `pandas` / `Series` 等底层细节
4. **双层 API**：
   - 便捷 API：覆盖常用指标（MA / EMA / RSI / MACD 等）
   - 通用 API：覆盖全部 `pandas-ta-classic` 指标
5. **无状态工具类**：
   - `IndicatorService` 采用类方法 / 静态方法，无需实例化，方便在任意上下文中调用

---

## 整体架构

### 模块关系

```text
业务模块 (strategy / tag / analyzer / ...)
        │
        ▼
  IndicatorService (core/modules/indicator)
        │
        ▼
  pandas-ta-classic (第三方指标库)
```

- 业务模块只依赖 `IndicatorService`，不直接面向 `pandas-ta-classic`
- `IndicatorService` 负责：
  - 将输入的 K 线数据转换成 `pandas.DataFrame`
  - 调用对应的 `pandas-ta-classic` 指标函数
  - 将结果转换回 `List[float]` 或 `Dict[str, List[float]]`

### 目录结构

```text
core/modules/indicator/
├── __init__.py            # 导出 IndicatorService
├── indicator_service.py   # IndicatorService 核心实现
└── README.md              # 面向开发者的使用说明
```

---

## 核心组件与职责

### IndicatorService

**职责**：

- 提供统一的技术指标计算接口
- 封装 `pandas-ta-classic` 的调用细节
- 统一处理输入 / 输出数据格式

**API 层次**：

1. **便捷 API（常用指标）**
   - 语义明确、参数默认值合理，适合日常调用
   - 示例：
     - `ma(klines, length=20)`
     - `ema(klines, length=12)`
     - `rsi(klines, length=14)`
     - `macd(klines, fast=12, slow=26, signal=9)`
     - `bbands(klines, length=20, std=2.0)`
     - `atr(klines, length=14)`
     - `stoch(klines, k=14, d=3, smooth_k=3)`
     - `adx(klines, length=14)`
     - `obv(klines)`

2. **通用 API**
   - `calculate(indicator_name: str, klines: List[Dict], **params) -> Any`
   - 允许业务方调用任意 `pandas-ta-classic` 指标，而不需要在 `IndicatorService` 中为每个指标写一层 wrapper

3. **辅助 API**
   - `list_indicators() -> List[str]`：列出所有可用指标
   - `get_indicator_help(name: str) -> str`：返回指定指标的帮助信息或参数说明

---

## 数据与调用流程

### 输入格式规范

Indicator 模块对输入 K 线数据采用统一的 Python 原生结构：

```python
klines = [
    {
        "date": "20251219",
        "open": 10.0,
        "high": 10.5,
        "low": 9.8,
        "close": 10.2,
        "volume": 1000,
    },
    # ...
]
```

- **必需字段**：`open`, `high`, `low`, `close`
- **可选字段**：`volume`, `date`

### 内部数据流

```text
1. 业务代码构造 klines（List[Dict]）
2. IndicatorService 将 klines 转为 DataFrame：
   - 列名映射：open / high / low / close / volume / date
3. 调用 pandas-ta-classic 对应函数：
   - e.g. ta.rsi(df["close"], length=14)
4. 将返回的 Series / DataFrame 转换为：
   - List[float]（单列）
   - Dict[str, List[float]]（多列）
5. 返回给业务代码
```

### 输出格式

- **单列指标**（如 MA / RSI / ATR）：

```python
[10.1, 10.2, 10.3, ...]  # List[float]
```

- **多列指标**（如 MACD / BBANDS）：

```python
{
    "MACD_12_26_9": [...],
    "MACDs_12_26_9": [...],
    "MACDh_12_26_9": [...],
}
```

---

## API 设计

### 便捷 API 设计原则

1. **命名与指标名一致**：如 `ma`, `ema`, `rsi`, `macd`，降低记忆成本
2. **合理默认值**：尽量提供交易中常用的默认参数（如 MA20、RSI14、MACD(12,26,9)）
3. **保持参数直观**：长度参数统一使用 `length`，避免每个指标一套叫法

示例：

```python
class IndicatorService:
    @classmethod
    def ma(cls, klines, length: int = 20):
        return cls.calculate("ma", klines, length=length)
```

### 通用 API 设计

```python
result = IndicatorService.calculate("cci", klines, length=20)
```

设计要点：

- `indicator_name` 对应 `pandas-ta-classic` 的函数名或别名
- `**params` 原样透传给底层指标函数
- 对于返回结构不统一的指标（多列），统一包装成 `Dict[str, List[float]]`

---

## 扩展与演进

短期计划：

- 补充更多便捷 API 覆盖最常用的几十个指标
- 在文档中列出推荐使用的指标组合和参数（如趋势 + 动量 + 波动度）

长期规划：

- 支持简单的 **组合指标**（如「MA 上穿 + RSI 超卖」的复合信号）
- 与 Tag / Strategy 模块更紧密集成，提供更高层的「因子」抽象

---

## 相关文档

- 模块 README：`core/modules/indicator/README.md`（详细使用说明）
- 架构总览：`docs/architecture/overview.md`
- 决策记录：`docs/architecture/core_modules/indicator/decisions.md`
