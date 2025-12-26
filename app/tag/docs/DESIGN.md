# Tag 系统架构设计文档

**版本：** 1.0  
**日期：** 2025-12-24  
**状态：** 设计阶段

---

## 📋 目录

1. [设计动机](#设计动机)
2. [核心设计思想](#核心设计思想)
3. [需要覆盖的场景](#需要覆盖的场景)
4. [系统架构](#系统架构)
5. [数据库设计](#数据库设计)
6. [Calculator 设计](#calculator-设计)
7. [执行流程](#执行流程)
8. [与 Labeler 的关系](#与-labeler-的关系)
9. [值缓存机制](#值缓存机制)

---

## 设计动机

### 问题背景

在策略回测中，经常需要根据股票的状态、特征等信息进行判断和筛选。这些判断逻辑可能：

1. **计算复杂且耗时**：如"牛市/熊市"划分需要分析长期趋势，遍历所有历史数据
2. **多策略复用**：多个策略都需要相同的标签（如"大市值"、"高动量"）
3. **需要提前预处理**：在回测时实时计算会影响回测速度
4. **数据一致性要求**：多个策略使用相同的标签定义，需要保证数据一致性

### 现有 Labeler 系统的局限性

现有的 `labeler` 系统存在以下局限性：

1. **固定时间切片**：只能按固定间隔（30天）计算标签，不够灵活
2. **单一计算模式**：只能返回标签ID字符串，不支持复杂的数据结构
3. **缺乏时间段支持**：无法表示标签的起始和结束时间
4. **难以扩展**：添加新的标签计算逻辑需要修改核心代码

### Tag 系统的设计目标

1. **灵活的标签计算**：支持自定义计算逻辑和定期切片两种模式
2. **时间段支持**：支持标签的起始和结束时间，满足连续标签和切片标签的需求
3. **配置驱动**：通过配置文件定义 tag，无需修改核心代码
4. **性能优化**：支持增量计算、多线程/进程并行计算
5. **存储层极简**：只负责存和查，不关心怎么算
6. **解释权在 Strategy**：tag 的值由 strategy 自己解释和使用

---

## 核心设计思想

### 1. Tag 是快速缓存机制（包含值缓存）

Tag 系统的本质是**一种提前计算的缓存机制**，用于：

- **性能优化**：避免在回测时重复计算相同的指标
- **多策略复用**：一次计算，多个策略使用
- **复杂计算预处理**：耗时计算提前完成，回测时直接查询
- **值缓存机制**：Tag 的 `value` 不仅可以存储分类标签，还可以存储计算值（如动量值、波动率等），用于横向切片和排序

**值缓存示例**：
- **月动量 Tag**：每个股票在每个月的第一天计算动量值，存储在 `value` 中（如 `"0.15"`）
- **策略使用**：回测时，查询所有股票的"月动量" tag，根据 `value` 进行排序，选出前10个
- **优势**：避免在回测时重新计算所有股票的动量，大大降低计算量和内存使用

**注意**：Tag 不是必须的，策略完全可以自己计算。Tag 的价值在于：
- 多策略复用场景
- 复杂计算场景
- 通用标签场景
- **值缓存场景**：需要横向切片和排序的场景（如每月动量前10）

### 2. 存储层极简，计算层灵活

- **存储层**：只负责存和查，不关心怎么算
- **计算层**：支持自定义 calculator，可以很复杂，但不影响存储层

### 3. 两种计算模式

Tag 系统支持两种计算模式：

- **自定义 Tag**：用户通过 calculator 定义计算逻辑，遍历历史数据
- **切片 Tag**：定期切片（如每月），系统自动生成切片，也可以有 calculator 计算切片内的值

### 4. 配置驱动

Tag 的定义和计算逻辑通过配置文件定义，无需修改核心代码。

**目录组织**：
- 每个 tag 类型一个文件夹（`app/tag/tags/<tag_name>/`）
- 每个文件夹包含：
  - `config.py`：Tag 配置（tag 元信息、计算参数等）
  - `calculator.py`：Tag 计算方法（继承 `BaseTagCalculator`）

**优势**：
- 便于管理：每个 tag 的逻辑独立
- 易于扩展：添加新 tag 只需新建文件夹
- 配置清晰：配置和计算逻辑分离

---

## 需要覆盖的场景

### 场景 A：连续但间隔不固定的 Tag

**示例**：市场状态划分（牛市、震荡市、熊市）

- **特点**：
  - 连续交替出现
  - 没有明确的结束时间（直到下一个状态开始）
  - 上一个 tag 的结束时间 = 下一个 tag 的开始时间 - 1 天

**实现**：
- 在 tag 配置中声明 `is_continuous: true`
- 系统自动处理连续关系：上一个 tag 的 `end_date` = 下一个 tag 的 `start_date` - 1 天

### 场景 B：定期切片 Tag（值缓存）

**示例**：每月动量最大的10个股票

- **特点**：
  - 有明确的起始和结束时间（一个月）
  - 定期重复（每月）
  - 需要提前计算，提升回测效率
  - **值缓存机制**：每个股票的动量值存储在 tag 的 `value` 中

**实现方式**：
1. **计算阶段**：
   - 在每个月的第一天，使用多线程按股票逐个计算动量值
   - 将动量值存储在"月动量" tag 的 `value` 中（如 `"0.15"`）
   - 每个股票一个 tag 记录，内存使用量低

2. **策略使用阶段**：
   - 查询所有股票的"月动量" tag
   - 根据 `value` 进行排序，选出前10个
   - 不需要重新计算，大大降低计算量和内存使用

**实现**：
- 在 tag 配置中声明 `type: "slice"` 和 `slice_policy: "MONTHLY"`
- 系统自动生成每月切片
- Calculator 计算每个股票的动量值，存储在 `value` 中

### 场景 C：离散的 Tag

**示例**：大市值股票（超过100亿市值）

- **特点**：
  - 一只股票可能出现多次
  - 每个 tag 有明确的起始和终点
  - 例如：市值超过100亿时打 tag，市值低于100亿时结束

**实现**：
- 在 tag 配置中声明 `type: "custom"`
- Calculator 遍历历史数据，根据市值变化决定 tag 的起始和结束

---

## 系统架构

### 目录结构

```
app/tag/
├── __init__.py
├── docs/
│   └── DESIGN.md          # 本文档
├── base_calculator.py     # Tag Calculator 基类
├── tag_service.py         # Tag 服务（主入口）
├── tag_executor.py        # Tag 执行器（多线程/进程）
└── tags/                  # Tag 实现目录（每个文件夹代表一类 tag）
    ├── __init__.py
    ├── market_regime/     # 市场状态 tag
    │   ├── config.py      # Tag 配置
    │   └── calculator.py  # Tag 计算方法
    ├── monthly_momentum/  # 月动量 tag
    │   ├── config.py
    │   └── calculator.py
    └── market_cap/        # 市值分类 tag
        ├── config.py
        └── calculator.py
```

**目录组织原则**：
- 每个 tag 类型一个文件夹
- 每个文件夹包含 `config.py`（tag 配置）和 `calculator.py`（计算方法）
- 便于管理和扩展

### 核心组件

1. **TagService**：主服务入口，负责 tag 的计算、存储和查询
2. **BaseTagCalculator**：Calculator 基类，提供钩子函数接口
3. **TagExecutor**：执行器，负责多线程/进程并行计算
4. **TagConfig**：配置管理器，加载和管理 tag 配置

---

## 数据库设计

### 1. `tag` 表（标签元信息）

```sql
CREATE TABLE tag (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(64) NOT NULL UNIQUE,      -- 标签唯一代码（machine readable）
    display_name    VARCHAR(128) NOT NULL,            -- 标签显示名称（用户可见）
    is_enabled      TINYINT(1) NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 2. `tag_value` 表（标签值存储）

```sql
CREATE TABLE tag_value (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    entity_id       VARCHAR(64) NOT NULL,            -- 实体ID（股票代码、指数代码等）
    tag_id          BIGINT NOT NULL,                 -- 标签ID（引用 tag.id）
    as_of_date      DATE NOT NULL,                   -- 业务日期（tag 创建时间）
    start_date      DATE NULL,                       -- tag 起始日期（时间切片 tag 用）
    end_date        DATE NULL,                       -- tag 结束日期（时间切片 tag 用）
    value           TEXT NOT NULL,                   -- 标签值（string，strategy 自己解释）
    calculated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tag (entity_id, tag_id, as_of_date),
    KEY idx_entity_date (entity_id, as_of_date),
    KEY idx_tag_date (tag_id, as_of_date)
);
```

**字段说明**：
- `start_date` / `end_date`：用于时间切片 tag 和连续 tag
- `value`：TEXT 类型，strategy 自己解释和解析
- `as_of_date`：tag 创建的时间点（业务日期）

---

## Calculator 设计

### BaseTagCalculator 基类

```python
class BaseTagCalculator(ABC):
    """Tag Calculator 基类"""
    
    def __init__(self, tag_id: int, tag_config: Dict[str, Any], data_mgr):
        self.tag_id = tag_id
        self.tag_config = tag_config
        self.data_mgr = data_mgr
    
    @abstractmethod
    def calculate_tag(
        self, 
        entity_id: str, 
        as_of_date: str, 
        historical_data: Dict[str, Any]  # 完整历史数据（上帝视角）
    ) -> Optional[TagEntity]:
        """
        钩子函数：在每个时间点调用
        
        Args:
            entity_id: 实体ID
            as_of_date: 当前时间点
            historical_data: 完整历史数据（上帝视角）
                - klines: 所有历史K线数据
                - finance: 所有历史财务数据
                - ... 其他历史数据
            
        Returns:
            TagEntity 或 None（不创建 tag）
        """
        pass
    
    def create_tag(
        self, 
        value: str,
        start_date: str = None,
        end_date: str = None
    ) -> TagEntity:
        """
        创建 Tag 实体（辅助方法）
        
        Args:
            value: 标签值（string）
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            TagEntity
        """
        return TagEntity(
            tag_id=self.tag_id,
            value=value,
            as_of_date=as_of_date,  # 从上下文获取
            start_date=start_date,
            end_date=end_date
        )
```

### TagEntity 结构

```python
@dataclass
class TagEntity:
    """Tag 实体"""
    tag_id: int
    value: str
    as_of_date: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
```

---

## 执行流程

### 1. 增量计算流程

```
1. 加载 tag 配置
2. 查询每个 (entity_id, tag_id) 的最大 as_of_date（最后计算时间点）
3. 从最后计算时间点 + 1 天开始计算
4. 遍历每个时间点，调用 calculator.calculate_tag()
5. 如果返回 TagEntity，保存到数据库
6. 如果是连续 tag，自动处理连续关系
```

### 2. 全量刷新流程

```
1. 加载 tag 配置
2. 删除该 tag 的所有历史数据（可选，或标记为旧版本）
3. 从 entity 的上市日期开始计算
4. 遍历所有时间点，调用 calculator.calculate_tag()
5. 保存所有计算结果
```

### 3. 多线程/进程执行

```
1. 将 entity 列表分成多个批次（每批最多10个）
2. 每个批次并行计算（多线程或多进程）
3. 每个线程处理一个 entity：
   - 加载该 entity 的完整历史数据
   - 遍历每个时间点，调用 calculator.calculate_tag()
   - 保存计算结果
   - 释放内存
4. 继续下一批次
```

**内存管理**：
- 每个线程只处理一个 entity，避免内存爆炸
- 计算完成后立即存储并释放内存
- 最多10个并行计算，控制内存使用

---

## 与 Labeler 的关系

### Labeler 的局限性

- **固定时间切片**：只能按固定间隔（30天）计算
- **单一计算模式**：只能返回标签ID字符串
- **缺乏时间段支持**：无法表示标签的起始和结束时间

### Tag 系统的扩展

Tag 系统是对 Labeler 的扩展和替代：

1. **灵活的标签计算**：支持自定义计算逻辑和定期切片
2. **时间段支持**：支持标签的起始和结束时间
3. **配置驱动**：通过配置文件定义 tag
4. **更灵活的数据结构**：支持复杂的数据结构（通过 value 字段）

### 迁移策略

- **短期**：Tag 系统和 Labeler 系统并存
- **长期**：逐步迁移到 Tag 系统，Labeler 标记为 legacy

---

## 设计决策

### 1. 为什么使用上帝视角？

- **计算效率**：遍历历史数据时，一次性加载所有数据更高效
- **灵活性**：Calculator 可以访问任意历史数据，满足复杂计算需求
- **责任清晰**：Calculator 作者负责是否使用未来数据，系统只提供数据

**注意**：如果 tag 用于回测，建议 Calculator 只使用 `as_of_date` 及之前的数据，避免数据泄露。

### 2. 为什么 Tag 的 value 可以作为值缓存？

**问题**：如果需要在回测时进行横向切片（如每月动量前10），传统方式需要：
- 加载所有股票的数据
- 计算所有股票的动量
- 排序选出前10个
- **问题**：内存爆炸，计算量大

**Tag 值缓存方案**：
- 提前计算：在每个月的第一天，使用多线程按股票逐个计算动量值
- 存储值：将动量值存储在 tag 的 `value` 中（如 `"0.15"`）
- 策略使用：查询所有股票的 tag，根据 `value` 排序，选出前10个
- **优势**：避免在回测时重新计算，大大降低计算量和内存使用

**示例**：
```python
# 计算阶段：每个股票计算动量值
tag_value = {
    "entity_id": "600000.SH",
    "tag_id": 1,  # 月动量 tag
    "as_of_date": "2025-01-01",
    "value": "0.15"  # 动量值
}

# 策略使用：查询所有股票的月动量，排序选出前10
all_tags = tag_service.get_all_entities_tags("2025-01-01", tag_id=1)
sorted_tags = sorted(all_tags, key=lambda x: float(x['value']), reverse=True)
top_10 = sorted_tags[:10]
```

### 2. 为什么统一为 tag 的两种模式？

- **用户视角简单**：只需要理解一套概念
- **查询接口统一**：无论是自定义 tag 还是切片 tag，查询方式相同
- **可以灵活组合**：切片 tag 也可以有 calculator 计算切片内的值

### 3. 为什么存储层极简？

- **职责清晰**：存储层只负责存和查，不关心怎么算
- **性能优先**：查询性能优先，索引针对核心查询优化
- **计算解耦**：计算复杂度由 calculator 处理，存储层不关心

### 4. 为什么 value 是 TEXT 而不是 JSON？

- **简单**：TEXT 类型更简单，不需要解析 JSON
- **灵活**：Strategy 自己解释和解析，系统不关心格式
- **安全**：避免 JSON 注入等安全问题
- **值缓存友好**：数值型 tag（如动量值）可以直接存储为字符串，查询时转换为数值进行排序

---

## 未来扩展

### 可能的扩展方向

1. **Tag 版本管理**：支持 tag 的版本管理，参数变化时自动创建新版本
2. **Tag 依赖关系**：支持 tag 之间的依赖关系（如 tag B 依赖 tag A）
3. **Tag 缓存机制**：支持 tag 的缓存，提升查询性能
4. **Tag 统计分析**：支持 tag 的统计分析（如 tag 覆盖率、tag 分布等）

---

## 值缓存机制

### 核心概念

Tag 的 `value` 不仅可以存储分类标签（如 `"LARGE_CAP"`），还可以存储计算值（如动量值 `"0.15"`），用于横向切片和排序。

### 典型场景：每月动量前10

**问题**：
- 策略需要每月选出动量最大的10个股票
- 如果回测时实时计算，需要加载所有股票数据，计算量大，内存爆炸

**Tag 值缓存方案**：

1. **计算阶段**（提前计算）：
   ```python
   # 在每个月的第一天，使用多线程按股票逐个计算
   for stock_id in stock_list:
       momentum_value = calculate_momentum(stock_id, month_start_date)
       tag_service.save_tag(
           entity_id=stock_id,
           tag_id=monthly_momentum_tag_id,
           as_of_date=month_start_date,
           value=str(momentum_value)  # 存储动量值
       )
   ```

2. **策略使用阶段**（回测时）：
   ```python
   # 查询所有股票的月动量 tag
   all_tags = tag_service.get_all_entities_tags(
       as_of_date="2025-01-01",
       tag_id=monthly_momentum_tag_id
   )
   
   # 根据 value 排序，选出前10
   sorted_tags = sorted(
       all_tags, 
       key=lambda x: float(x['value']), 
       reverse=True
   )
   top_10_stocks = [tag['entity_id'] for tag in sorted_tags[:10]]
   ```

**优势**：
- **计算量降低**：避免在回测时重新计算所有股票的动量
- **内存使用降低**：不需要同时加载所有股票的数据
- **性能提升**：回测时只需要查询和排序，速度更快

### 值缓存 vs 分类标签

| 类型 | 示例 | value 格式 | 使用场景 |
|------|------|------------|----------|
| 分类标签 | 市值分类 | `"LARGE_CAP"` | 用于过滤和分组 |
| 值缓存 | 月动量 | `"0.15"` | 用于排序和横向切片 |

---

## 总结

Tag 系统是一个**灵活的标签计算和存储框架**，用于：

- **性能优化**：避免在回测时重复计算
- **多策略复用**：一次计算，多个策略使用
- **复杂计算预处理**：耗时计算提前完成
- **值缓存机制**：存储计算值，支持横向切片和排序

**核心设计原则**：
- 存储层极简：只负责存和查
- 计算层灵活：支持自定义 calculator
- 配置驱动：通过配置文件定义 tag
- 解释权在 Strategy：tag 的值由 strategy 自己解释
- **值缓存支持**：tag 的 value 可以作为值缓存，支持横向切片和排序
