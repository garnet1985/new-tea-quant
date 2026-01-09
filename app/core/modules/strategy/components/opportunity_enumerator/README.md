# Opportunity Enumerator

## 概述

OpportunityEnumerator 是一个**机会枚举器**，负责**完整枚举**策略的所有投资机会。

### 核心特点

- ✅ **完整枚举**：每天都扫描，不跳过任何可能的机会
- ✅ **同时追踪多个机会**：即使已有持仓也继续查找新机会
- ✅ **完整记录**：每个机会独立追踪，记录 `completed_targets`
- ✅ **使用 Opportunity 实例方法**：`check_targets()`, `settle()`
- ✅ **CSV 存储**：高性能，Excel 可直接打开
- ✅ **每次重新计算**：保证结果反映最新策略代码
- ✅ **多进程并行**：高效处理大量股票

---

## 使用方法

```python
from app.core.modules.strategy.components.opportunity_enumerator import OpportunityEnumerator

# 方式 1：自动计算 worker 数量（推荐）⭐
all_opportunities = OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',
    end_date='20231231',
    stock_list=['000001.SZ', '000002.SZ', ...],
    max_workers='auto'  # ✅ 自动计算（根据任务类型和 CPU 核心数）
)

# 方式 2：手动指定 worker 数量
all_opportunities = OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',
    end_date='20231231',
    stock_list=['000001.SZ', '000002.SZ', ...],
    max_workers=10  # ✅ 手动指定（会自动保护，最多 2 倍 CPU 核心数）
)

print(f"找到 {len(all_opportunities)} 个机会")
```

---

## 与 Simulator 的区别

| 特性 | Simulator | OpportunityEnumerator |
|------|-----------|----------------------|
| **持仓限制** | 同时只能持有 1 个 | 同时追踪多个（可重叠） |
| **扫描频率** | 无持仓时才扫描 | 每天都扫描（完整枚举） |
| **输出** | 主线机会（一条路径） | 所有可能机会（多条路径） |
| **用途** | 策略验证（主线回测） | 完整枚举（供 Allocation 使用） |
| **输出格式** | JSON | CSV 双表 |

### 示例对比

```
Simulator（主线，单一路径）：
1月1日：发现机会A，买入
1月2日：持有A（❌ 不扫描）
1月3日：持有A（❌ 不扫描）
1月5日：A完成（止盈）
1月6日：发现机会D，买入
...

Enumerator（完整枚举，所有路径）：
1月1日：发现机会A，开始追踪
1月2日：继续追踪A + ✅ 发现机会B，开始追踪B
1月3日：继续追踪A和B + ✅ 发现机会C，开始追踪C
1月5日：A完成（止盈） + 继续追踪B和C
1月9日：C完成（止损） + 继续追踪B
...
```

**关键区别**：
- Simulator：模拟实际交易（一次只买一个）
- Enumerator：枚举所有可能（同时追踪多个）

---

## 输出结构

### 文件结构

```
app/userspace/strategies/{strategy_name}/results/opportunity_enums/
├── meta.json                       # 版本管理元信息（自增 ID）
└── {version_dir}/                  # 每次运行一个版本目录
    ├── metadata.json               # 本次运行的元信息（含 settings 快照）
    ├── 000001.SZ_opportunities.csv # 股票 000001.SZ 的机会列表
    ├── 000001.SZ_targets.csv      # 股票 000001.SZ 的 completed_targets
    ├── 000002.SZ_opportunities.csv # 股票 000002.SZ 的机会列表
    ├── 000002.SZ_targets.csv      # 股票 000002.SZ 的 completed_targets
    └── ...                         # 其他股票的 CSV 文件
```

**说明**：
- `meta.json` 只在 `opportunity_enums/` 目录下维护一个简单的自增 ID，例如：
  - `{"next_version_id": 3, "last_updated": "...", "strategy_name": "momentum"}`
- 每次运行：
  - 读取 `meta.json` 中的 `next_version_id`
  - 生成版本目录名：`{version_id}_{YYYYMMDDHHMMSS}`（例如 `3_20260109_153045`）
  - 把本次结果写入该目录，并更新 `meta.json`
- **不覆盖旧结果**，每次运行都会产生一个新版本目录，方便回溯与对比
- **Per-stock CSV**：每只股票在子进程结束时各自写出独立的 CSV 文件，主进程不做合并（降低内存占用，便于调试）
- CSV 文件可用 Excel 直接打开

### {stock_id}_opportunities.csv

```csv
opportunity_id,stock_id,stock_name,strategy_name,trigger_date,trigger_price,status,price_return,extra_fields
uuid-1,000001.SZ,平安银行,momentum,20230115,10.50,completed,0.067,"{\"momentum\": 0.12}"
uuid-2,000001.SZ,平安银行,momentum,20230116,10.55,completed,-0.023,"{\"momentum\": -0.03}"
```

**字段说明**：
- `opportunity_id`：机会唯一 ID
- `stock_id` / `stock_name`：股票代码和名称
- `trigger_date` / `trigger_price`：触发日期和价格
- `exit_date` / `exit_price` / `exit_reason`：退出信息（与 `trigger_*` 对称）
- `price_return`：价格收益率（不再使用 `roi` 字段名）
- `extra_fields`：JSON 字符串，承载用户扩展字段（如因子值、打分等）
  - 框架**不会解析或裁剪**其中内容，只是原样写入 CSV

### {stock_id}_targets.csv

```csv
opportunity_id,date,price,reason,roi,sell_ratio,extra_fields
uuid-1,20230125,11.20,take_profit_stage1,0.067,0.5,"{\"triggered_by_target\": \"win10%\"}"
uuid-1,20230130,11.50,take_profit_stage2,0.095,0.5,"{\"triggered_by_action\": \"set_dynamic_loss\"}"
uuid-2,20230120,10.31,stop_loss,-0.023,1.0,"{}"
```

**说明**：
- 一条 `opportunity` 可能对应多条 `target` 记录（分段止盈止损、到期平仓等）
- `extra_fields` 同样以 JSON 字符串形式保存 target 级别的额外信息

### metadata.json

```json
{
  "strategy_name": "momentum",
  "start_date": "20230101",
  "end_date": "20231231",
  "opportunity_count": 5234,
  "created_at": "2026-01-09T15:30:45.123456",
  "version_id": 3,
  "version_dir": "3_20260109_153045",
  "settings_snapshot": { ... 完整 settings 字典 ... }
}
```

**说明**：
- `settings_snapshot`：保存本次枚举时使用的完整 settings（经过校验和默认值补全后的版本）
- 即使用户后续修改了 `settings.py`，也能通过此快照精确还原当时的配置

---

## 工作原理

### 整体流程

```
主进程（OpportunityEnumerator）：
  1. 加载策略 settings → StrategySettings（baseSetting）
  2. 创建 OpportunityEnumeratorSettings（组合视图，校验+补全）
  3. 准备版本目录（meta.json 自增 ID）
  4. 构建 jobs（每只股票一个 job）
  5. 使用 ProcessWorker 多进程执行
  6. 聚合 summary（只拿 opportunity_count，不拉回全量数据）
  7. 写入 metadata.json

子进程（OpportunityEnumeratorWorker）：
  1. 加载全量 K 线（根据 settings.data.base/adjust）
  2. 一次性计算技术指标（根据 settings.data.indicators）
  3. 加载 required_entities（GDP、tag 等）
  4. 逐日迭代：
     - 用游标获取“截至今天”的数据快照
     - 检查所有 active opportunities 是否完成
     - 调用用户 scan_opportunity() 扫描新机会
  5. 进程结束前：写出本股票的 CSV（{stock_id}_opportunities.csv + targets.csv）
  6. 返回轻量 summary（success, stock_id, opportunity_count）
  7. 进程结束，内存自动释放
```

### Settings 处理（两层架构）

**设计**：BaseSetting（通用）+ 组件视图（组合）

```python
# 1. 通用 StrategySettings（所有模块共用）
base_settings = StrategySettings.from_dict(module.settings)

# 2. 枚举器专用视图（组合，而非继承）
enum_settings = OpportunityEnumeratorSettings.from_base(base_settings)
validated_settings = enum_settings.to_dict()  # 已校验+补全默认值

# 3. 传给 Worker
job = {
    'settings': validated_settings,  # 只传校验后的配置
    ...
}
```

**OpportunityEnumeratorSettings 职责**：
- ✅ 检查必要字段（`data.base`, `data.adjust` 必须存在）
- ✅ 补全可选字段（`data.min_required_records` 默认 100，`data.indicators` 默认 `{}`，`simulator.goal` 默认 `{}`）
- ✅ 返回“已校验 & 补全”的 settings 视图（其他字段如 `core/performance` 原样保留）

### 数据准备机制

**1. 主 K 线（base）**：
- 从 `settings.data.base` / `settings.data.adjust` 解析出 term 和复权方式
- 在子进程中为当前股票加载 `[actual_start_date, end_date]` 区间的全量 K 线

**2. 技术指标计算**：
- 根据 `settings.data.indicators`，使用 `IndicatorService` 在子进程里**一次性计算**所有指标
- 结果直接写回每条 kline 的 dict（例如 `ma5`, `rsi14`, `macd` 等）
- **重要**：虽然一次性计算，但通过游标 `get_data_until(date)` 切片时，只会看到 `date <= T` 的数据，避免上帝模式

**3. Required Entities**：
- 根据 `settings.data.required_entities`，在子进程里加载 tag / corporate_finance / gdp 等全量数据
- 同样通过游标机制，每天只提供“截至今天”的 entity 列表

**4. 游标机制（避免上帝模式）**：
```python
# 在子进程里，一次性加载全量数据
all_klines = load_historical_data(...)  # 包含指标
all_entities = load_required_entities(...)

# 逐日迭代时，用游标获取“截至今天”的快照
for current_kline in all_klines:
    date_of_today = current_kline['date']
    data_of_today = data_manager.get_data_until(date_of_today)
    # data_of_today = {
    #   'klines': [... 只包含 date <= date_of_today 的 K 线 ...],
    #   'gdp': [... 只包含 date <= date_of_today 的 GDP ...],
    #   ...
    # }
    opportunity = scan_opportunity_with_data(data_of_today)
```

### 核心逻辑

```python
class OpportunityEnumeratorWorker:
    def _enumerate_single_day(self, tracker, current_kline, data_of_today):
        # 1. 检查所有 active opportunities
        for opportunity in tracker['active_opportunities']:
            is_completed = opportunity.check_targets(
                current_kline=current_kline,
                goal_config=self.settings.goal
            )
            
            if is_completed:
                # 移出 active list
                pass
        
        # 2. 扫描新机会（⭐ 不管是否有持仓）
        new_opportunity = self._scan_opportunity_with_data(data_of_today)
        
        if new_opportunity:
            tracker['active_opportunities'].append(new_opportunity)
            tracker['all_opportunities'].append(new_opportunity)
```

### Opportunity 实例方法

```python
class Opportunity:
    def check_targets(self, current_kline, goal_config) -> bool:
        """检查止盈止损"""
        # 检查各种止盈止损条件
        if completed:
            self._settle(...)  # 内部结算
            return True
        return False
    
    def settle(self, last_kline, reason='backtest_end'):
        """强制结算（回测结束时）"""
        self._settle(...)
```

### 进程执行与内存管理

**主进程职责**：
- ✅ 只负责调度：解析 settings、构建 jobs、启动 ProcessWorker、聚合 summary、写入 metadata.json
- ❌ 不加载 K 线、不计算指标、不执行策略逻辑

**子进程职责**：
- ✅ 加载数据：K 线 + required_entities（全量，一次性）
- ✅ 计算指标：根据 `settings.data.indicators` 一次性计算并写回 klines
- ✅ 迭代 K 线：逐日推进，用游标获取“截至今天”的数据快照
- ✅ 执行策略：调用用户 `scan_opportunity()`，追踪 opportunities
- ✅ 写盘：进程结束前，写出本股票的 CSV（`{stock_id}_opportunities.csv` + `targets.csv`）
- ✅ 返回：只返回轻量 summary（`success`, `stock_id`, `opportunity_count`），不返回全量 opportunities 列表

**内存释放**：
- 子进程结束时，Worker 实例销毁，`_current_data` 和 `_cursor_state` 自动被垃圾回收
- 主进程不持有全量 opportunities 列表，只聚合 summary 信息
- 如需进一步优化，可在 Worker 结束时显式清理引用（`self._current_data = None` 等）

**进度提示**：
- ProcessWorker 内部会输出每 N 个 job 的进度（例如 "Progress: 20/100 jobs submitted"）
- 枚举器主进程会输出最终统计（成功/失败股票数、总机会数）

---

## 使用场景

### 场景 1：开发调试（快速验证）

```python
# 缩小范围
OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',
    end_date='20230110',     # ⭐ 只测试 10 天
    stock_list=['000001.SZ'], # ⭐ 只测试 1 只股票
    max_workers=1            # ⭐ 单进程，方便调试
)
```

### 场景 2：完整回测（全量历史）

```python
# 完整枚举（注意：Layer 0 始终从 DEFAULT_START_DATE 开始加载全量历史）
OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    start_date='20230101',      # 仅用于 metadata 记录 & 上层消费窗口
    end_date='20231231',
    stock_list=all_stocks,      # ⭐ 所有股票
    max_workers=10              # ⭐ 全速并行
)
```

> 关键点：
> - **枚举器始终做“全量历史枚举”**：真实加载的数据范围从统一的 `DateUtils.DEFAULT_START_DATE` 开始，到 `end_date` 为止；
> - `start_date` 参数只影响：
>   - metadata 里的记录范围；
>   - 上层应用如何切片使用这些机会（例如只分析某个时间窗口）。

### 场景 3：CapitalAllocationSimulator 使用（未来）

```python
# Allocation 会自动调用 Enumerator
allocation_simulator.run(
    strategies=['momentum', 'value'],
    start_date='20230101',
    end_date='20231231',
    capital=100000
)
# 内部会调用 OpportunityEnumerator.enumerate(...)
```

---

## 性能

**测试场景**：100 股票，250 交易日

| 指标 | 预估值 | 说明 |
|------|--------|------|
| 枚举时间 | 30-60 秒 | 取决于策略复杂度 |
| CSV 文件大小 | 1-5 MB | 取决于机会数量 |
| 并行效率 | 线性加速 | `max_workers` 可调 |

**优化建议**：
- 调试时缩小范围（股票数量、时间范围）
- 生产环境增加 `max_workers`

---

## 常见问题

**Q: 每次都要重新计算吗？会不会很慢？**  
A: 是的，每次都重新计算。但这保证结果始终反映最新策略代码。如果需要缓存，将来在 `CapitalAllocationSimulator` 层实现。

**Q: 能不能读取之前的结果？**  
A: 可以，直接读取 per-stock CSV：
```python
import pandas as pd
# 读取单只股票的机会
df = pd.read_csv('app/userspace/strategies/momentum/results/opportunity_enums/3_20260109_153045/000001.SZ_opportunities.csv')
# 读取对应的 targets
targets = pd.read_csv('app/userspace/strategies/momentum/results/opportunity_enums/3_20260109_153045/000001.SZ_targets.csv')
```

**Q: 枚举时间太长怎么办？**  
A: 
1. 增加 `max_workers`（如 20）
2. 缩小股票范围（先测试部分股票）
3. 缩小时间范围（先测试一个月）

**Q: 和 Simulator 有什么区别？**  
A: 
- **Simulator**：单一主线（模拟实际交易）
- **Enumerator**：完整枚举（所有可能的机会）
- Enumerator 的结果会被 `CapitalAllocationSimulator` 使用

---

## 数据定义（枚举器视角）

> 这里只定义 **枚举器自己关心的字段**；真实的 `Opportunity` 对象可以比 CSV 多字段，但在落盘时至少要满足下述约定，才能保证 Allocation / Analyzer 等上层模块有稳定输入。

### 1. 内存中的 Opportunity 结构（简化视图）

在枚举器的子进程里，我们使用的是 `app.core.modules.strategy.models.opportunity.Opportunity` 数据类。  
从枚举器视角，至少会用到这些字段：

- **标识 & 基本信息**
  - `opportunity_id: str`：唯一 ID（UUID，可由策略决定，但要求在一次运行内唯一）
  - `stock: Dict[str, Any]`：股票元信息（结构与 legacy 对齐），至少包含：
    - `id`: `"000001.SZ"`
    - `name`: `"平安银行"`
    - `industry`: `"银行"`
    - `type`: `"主板"`
    - `exchange_center`: `"SZSE"`
  - `stock_id: str`：冗余字段，等于 `stock["id"]`
  - `stock_name: str`：冗余字段，等于 `stock["name"]`
  - `strategy_name: str`
  - `strategy_version: str`
- **触发信息**
  - `scan_date: str`：扫描发生的日期（一般为今天）
  - `trigger_date: str`：机会对应的“买入日”（通常等于当前 K 线日期）
  - `trigger_price: float`
  - `trigger_conditions: Dict[str, Any]`：触发时的条件快照（例如 `{"ma20": 10.23, "rsi14": 68.2, "signal": "price_breakout_ma20"}`）
- **结果信息（价格层面）**
  - `exit_date: Optional[str]`：退出日期（与 `trigger_date` 对称）
  - `exit_price: Optional[float]`：退出价格
  - `exit_reason: Optional[str]`：如 `take_profit_win10%` / `stop_loss_loss20%` / `expiration` / `enumeration_end` / `open`
  - `price_return: Optional[float]`：价格收益率 \((exit\_price - trigger\_price) / trigger\_price\)
- **轨迹 & 统计**
  - `holding_calendar_days: Optional[int]`：自然日持有天数（触发日起算，使用日期差）
  - `holding_trading_days: Optional[int]`：交易日持有天数（按枚举时实际经历的 K 线条数统计）
  - `max_price: Optional[float]`：持有期间最高价（收盘价）
  - `min_price: Optional[float]`：持有期间最低价（收盘价）
  - `max_return: Optional[float]`：\((max\_price - trigger\_price) / trigger\_price\)
  - `min_return: Optional[float]`：\((min\_price - trigger\_price) / trigger\_price\)
  - `max_drawdown: Optional[float]`：最大回撤（从最高点回落的最差收益率）
- **枚举器专用**
  - `completed_targets: Optional[List[Dict[str, Any]]]`：
    - 每个元素至少包含：`date`, `price`, `reason`, `roi`, `sell_ratio`（可选），以及用户策略塞进去的任意 `extra_fields`
  - `status: str`：`active` / `completed` / `expired` / `open` 等
  - `expired_date: Optional[str]`
  - `expired_reason: Optional[str]`
- **扩展 & 元信息**
  - `metadata: Dict[str, Any]`
  - `config_hash: str`：由当前 settings 计算出的 hash，用于追踪“此机会对应的是哪版配置”

> 要点：  
> - **completed_targets 必须完整**：止盈、止损、到期、强制结算（open）都要落在这里。  
> - `to_dict()` 必须在不丢字段的前提下工作，枚举器直接依赖 `to_dict()` 结果写 CSV。

### 2. opportunities.csv 列约定（最小必要集）

最小列集（上层模块可以只依赖这些列工作）：

- `opportunity_id`
- `stock_id`
- `stock_name`
- `stock_industry`（可选，来自 `stock["industry"]`）
- `stock_type`（可选，来自 `stock["type"]`）
- `stock_exchange_center`（可选，来自 `stock["exchange_center"]`）
- `strategy_name`
- `strategy_version`
- `scan_date`
- `trigger_date`
- `trigger_price`
- `exit_date`
- `exit_price`
- `exit_reason`
- `price_return`
- `status`
- `config_hash`
- `created_at`
- `updated_at`
- `extra_fields`：JSON 字符串，对应 `Opportunity` 上的扩展字段

> 实现层面：  
> - **不做列过滤**：`to_dict()` 里有的 key 都写入 CSV，未知字段统一走 `extra_fields` 或直接当顶层列写出。  
> - 上层使用方只依赖上面这部分“稳定约定”的列，其余列视为“附加信息”。

### 3. targets.csv 列约定（completed_targets 明细）

来自 `Opportunity.completed_targets` 中的每个元素，最小列集：

- `opportunity_id`
- `date`
- `price`
- `reason`：如 `take_profit_win10%` / `stop_loss_loss20%` / `expiration` / `open`
- `roi`
- `sell_ratio`：本次动作卖出的比例（0~1）
- `extra_fields`：JSON 字符串，用于记录触发信息，如：
  - `{"triggered_by_target": "win10%", "triggered_by_action": "set_dynamic_loss"}`

> 生成策略：  
> - 每条 `completed_targets` 记录是一个 **事件**；  
> - 不做再加工，原样序列化为一行 CSV，保证 ML / Allocation 等可以做事件级别分析。

### 4. metadata.json 结构（每个版本目录内）

每次运行在版本目录中写一个 `metadata.json`，用于描述本次枚举任务本身：

示例：

```json
{
  "strategy_name": "momentum",
  "version_id": 3,
  "start_date": "20230101",
  "end_date": "20231231",
  "stock_list": ["000001.SZ", "000002.SZ"],
  "opportunity_count": 5234,
  "created_at": "2026-01-09T15:30:45.123456",
  "settings_snapshot": { ... 完整 settings 字典 ... }
}
```

设计要点：

- `settings_snapshot`：直接保存当时使用的 `settings.to_dict()`，即使用户以后修改了 `settings.py`，也能精确还原当时的配置。
- `stock_list`：写入实际参与枚举的股票 ID 列表（可以只存一部分，如前 N 个，视性能权衡；这点可以留给实现阶段微调）。

### 5. meta.json 结构（opportunity_enums 根目录）

用于管理版本自增 ID，legacy 风格的简单 meta：

```json
{
  "next_version_id": 4,
  "last_updated": "2026-01-09T15:30:45.123456",
  "strategy_name": "momentum"
}
```

使用规则：

1. 如果 `meta.json` 不存在：初始化为 `{"next_version_id": 1, ...}`。
2. 每次运行：
   - 读取 `next_version_id` 作为本次 `version_id`
   - 创建目录：`{version_id}_{YYYYMMDDHHMMSS}`（例如 `3_20260109_153045`）
   - 完成写入后，把 `next_version_id` 更新为 `version_id + 1`，`last_updated` 写当前时间。

---

## 伪代码：整体流程（不含实现细节）

> 下面是当前组件实现的“设计版”轮廓，真实代码可以在此基础上填充细节和错误处理。

### 1. 主入口：OpportunityEnumerator.enumerate(...)

```python
def enumerate(strategy_name, start_date, end_date, stock_list, max_workers='auto') -> List[Dict]:
    # 1. 解析 worker 数量（使用 ProcessWorker.resolve_max_workers）
    workers = resolve_max_workers(max_workers, module_name='OpportunityEnumerator')

    # 2. 加载策略 settings（userspace/{strategy_name}/settings.py）
    settings = load_strategy_settings(strategy_name)

    # 3. 构建 jobs（每只股票一个 job）
    jobs = []
    for stock_id in stock_list:
        jobs.append({
            'stock_id': stock_id,
            'strategy_name': strategy_name,
            'settings': settings.to_dict(),
            'start_date': start_date,
            'end_date': end_date,
        })

    # 4. 使用 ProcessWorker 多进程执行
    #    job_executor: _execute_single_job(payload) -> {success, stock_id, opportunities: [...]}
    job_results = run_with_process_worker(
        jobs=jobs,
        max_workers=workers,
        job_executor=_execute_single_job
    )

    # 5. 聚合所有股票的 opportunities
    all_opportunities = []
    for r in job_results:
        if r['success']:
            all_opportunities.extend(r['opportunities'])
        else:
            log_warning(...)

    # 6. 生成版本目录（使用 meta.json 管理 next_version_id）
    version_dir = prepare_version_directory(strategy_name, start_date, end_date)

        # 7. 写入 metadata.json（含 settings_snapshot、版本信息）
        #    注意：CSV 已由各子进程在 job 结束时各自写出，主进程不再合并
        save_metadata(
            output_dir=version_dir,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            version_id=next_version_id,
            version_dir_name=version_dir_name,
            opportunity_count=total_opportunities,
            settings_snapshot=validated_settings
        )

        # 8. 返回 summary（不再返回全量 opportunities 列表）
        return [{
            'strategy_name': strategy_name,
            'version_id': next_version_id,
            'version_dir': version_dir_name,
            'opportunity_count': total_opportunities,
            'success_stocks': success_count,
            'failed_stocks': failed_count,
        }]
```

### 2. 主进程 job_executor：_execute_single_job(...)

```python
def _execute_single_job(payload: Dict) -> Dict:
    """
    在子进程内执行的包装函数：
    - 动态加载策略 Worker 类
    - 构造 OpportunityEnumeratorWorker
    - 调用 worker.run()
    """
    try:
        worker = OpportunityEnumeratorWorker(payload)
        result = worker.run()
        return result
    except Exception as e:
        return {
            'success': False,
            'stock_id': payload.get('stock_id'),
            'opportunities': [],
            'error': str(e),
        }
```

### 3. 子进程 Worker：OpportunityEnumeratorWorker.run()

```python
def run(self) -> Dict:
    # 1. 根据 settings.min_required_records 计算 lookback_days（上限例如 60）
    lookback_days = min(self.settings.min_required_records, 60)
    actual_start_date = get_date_before(self.start_date, lookback_days)

    # 2. 通过 StrategyWorkerDataManager 加载 [actual_start_date, end_date] 区间的全量数据
    #    2.1 加载 K 线（根据 settings.data.base/adjust）
    self.data_manager.load_historical_data(actual_start_date, self.end_date)
    #    2.2 一次性计算技术指标（根据 settings.data.indicators）
    #        - 指标结果直接写回每条 kline 的 dict（例如 ma5, rsi14, macd）
    #        - 在 StrategyWorkerDataManager._apply_indicators() 中完成
    #    2.3 加载 required_entities（GDP、tag 等）
    #        - 在 load_historical_data() 中自动完成

    all_klines = self.data_manager.get_klines()
    if not all_klines:
        return { 'success': True, 'stock_id': self.stock_id, 'opportunity_count': 0 }

    # 3. 初始化 tracker
    tracker = {
        'stock_id': self.stock_id,
        'passed_dates': [],
        'active_opportunities': [],   # 当前仍在持有/追踪中的机会（Opportunity 对象）
        'all_opportunities': []       # 所有机会（包括未完成但在结束时被 settle 掉的）
    }

    # 4. 按时间顺序逐日推进
    last_kline = None
    for current_kline in all_klines:
        virtual_date = current_kline['date']
        tracker['passed_dates'].append(virtual_date)

        # 4.1 未达到最小 K 线数时跳过（不足以计算指标/信号）
        if len(tracker['passed_dates']) < self.settings.min_required_records:
            continue

        # 4.2 用“游标”获取截至今天的数据快照，避免上帝模式
        #     游标机制：只 append 新增数据，不重新切片，提高效率
        data_of_today = self.data_manager.get_data_until(virtual_date)
        #     data_of_today = {
        #       'klines': [... 只包含 date <= virtual_date 的 K 线（已含指标）...],
        #       'gdp': [... 只包含 date <= virtual_date 的 GDP ...],
        #       ...
        #     }

        # 4.3 检查所有 active_opportunities 是否完成
        check_and_close_active_opportunities(
            tracker=tracker,
            current_kline=current_kline,
            goal_config=self.settings.goal
        )

        # 4.4 即使有持仓，也始终扫描新的机会（完整枚举）
        new_opp = scan_new_opportunity_with_data(
            strategy_instance=self.strategy_instance,
            data_of_today=data_of_today,
            current_kline=current_kline,
            stock_id=self.stock_id,
            strategy_name=self.strategy_name
        )
        if new_opp is not None:
            tracker['active_opportunities'].append(new_opp)
            tracker['all_opportunities'].append(new_opp)

        last_kline = current_kline

    # 5. 回测结束，对仍未完成的机会执行强制结算（reason='enumeration_end'）
    if tracker['active_opportunities'] and last_kline is not None:
        force_settle_all_open_opportunities(tracker, last_kline)

    # 6. 序列化并写出本股票的 CSV（进程结束前）
    opportunities_dicts = [opp.to_dict() for opp in tracker['all_opportunities']]
    output_dir = self.job_payload.get('output_dir')
    if output_dir and opportunities_dicts:
        self._save_stock_results(output_dir, opportunities_dicts)
        # 写出：{stock_id}_opportunities.csv 和 {stock_id}_targets.csv

    # 7. 清理内存引用（可选，但推荐）
    tracker.clear()
    self.data_manager._current_data.clear()

    # 8. 返回轻量 summary（不返回全量 opportunities 列表）
    return {
        'success': True,
        'stock_id': self.stock_id,
        'opportunity_count': len(opportunities_dicts),
    }
```

> 注意：  
> - 第 4.3 / 4.5 中 “检查 / 结算” 都是通过 `Opportunity.check_targets()` / `Opportunity.settle()` 来完成，  
>   Worker 不自己实现止盈止损逻辑，只负责调度。

---

## 设计原则

1. **完整性 > 性能**：不为性能牺牲准确性，确保每个可能机会都被记录
2. **简单 > 复杂**：专注于“生成 + 落盘”，不在此层做 cache 或读取逻辑
3. **每次重新计算**：每次运行都从头枚举一遍，保证结果与当前策略代码和 settings 一致
4. **职责单一**：
   - 只负责：在子进程中加载数据、调用 `scan_opportunity()`、维护 Opportunity 生命周期、写出 CSV + metadata + settings 快照
   - 不负责：读取 CSV、版本选择、结果分析（这些由上层应用或辅助类负责）

---

**版本**：2.0（枚举器组件版）  

---

**版本**：2.0（枚举器组件版）  
**完成时间**：2026-01-08
