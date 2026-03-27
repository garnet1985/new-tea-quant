# Version Manager - 统一版本管理器

## 📋 概述

`VersionManager` 是策略模块的统一版本管理器，负责管理所有组件的版本目录创建和解析。它消除了各组件中重复的版本管理代码，提供了统一的接口和一致的版本管理逻辑。

## 🎯 设计目标

1. **统一接口**：所有组件使用相同的版本管理接口
2. **消除重复**：避免各组件重复实现版本管理逻辑
3. **易于维护**：版本管理逻辑集中管理，便于修改和扩展
4. **简洁清晰**：提供统一的 `resolve_sot_version` 方法（机会池版本）作为通用接口

## 📦 功能特性

### 支持的组件类型

1. **枚举器（Opportunity Enumerator）**
   - 支持 `test/` 和 `pool/` 两个子目录
   - 根据 `use_sampling` 参数自动选择子目录

2. **价格因子模拟器（Price Factor Simulator）**
   - 独立的版本管理
   - 支持对同一 枚举输出版本进行多轮模拟对比

3. **资金分配模拟器（Capital Allocation Simulator）**
   - 独立的版本管理
   - 支持对同一 枚举输出版本进行多轮模拟对比

### 版本目录格式

所有版本目录统一使用以下格式：

```
{version_id}
```

例如：`1`

### Meta.json 管理

每个版本管理目录都有一个 `meta.json` 文件，用于记录：
- `next_version_id`：下一个版本ID
- `last_updated` / `last_created_at`：最后更新时间
- `strategy_name`：策略名称
- 其他元信息（如 `mode` 用于枚举器）

## 🔧 API 文档

### 枚举器版本管理

#### `create_enumerator_version(strategy_name, use_sampling=False)`

创建枚举器版本目录（机会池或测试采样）。

**参数**：
- `strategy_name` (str): 策略名称
- `use_sampling` (bool): 是否使用采样模式
  - `True`: 使用 `test/` 子目录（采样）
  - `False`: 使用 `pool/` 子目录（完整机会池）

**返回**：
- `(version_dir, version_id)`: 版本目录路径和版本ID

**示例**：
```python
from app.core.modules.strategy.managers.version_manager import VersionManager

# 创建 枚举输出版本（完整枚举）
version_dir, version_id = VersionManager.create_enumerator_version(
    strategy_name="example",
    use_sampling=False
)

# 创建测试版本（采样枚举）
version_dir, version_id = VersionManager.create_enumerator_version(
    strategy_name="example",
    use_sampling=True
)
```

#### `resolve_enumerator_version(strategy_name, version_spec)`

解析枚举器版本目录。

**支持的格式**：
- `"latest"`: 使用最新的机会池版本（`pool/` 目录）
- `"test/latest"`: 使用最新的测试版本（`test/` 目录）
- `"pool/latest"`: 使用最新的机会池版本（`pool/` 目录）
- `"1"`: 使用指定版本号（默认在 `pool/` 目录查找）
- `"test/1"`: 使用指定测试版本号（`test/` 目录）
- `"pool/1"`: 使用指定机会池版本号（`pool/` 目录）

**参数**：
- `strategy_name` (str): 策略名称
- `version_spec` (str): 版本标识符

**返回**：
- `(version_dir, base_dir)`: 版本目录路径和基础目录路径

**示例**：
```python
# 使用最新 枚举输出版本
version_dir, base_dir = VersionManager.resolve_enumerator_version(
    strategy_name="example",
    version_spec="latest"
)

# 使用指定测试版本
version_dir, base_dir = VersionManager.resolve_enumerator_version(
    strategy_name="example",
    version_spec="test/1_20260112_161317"
)
```

### 价格因子模拟器版本管理

#### `create_price_factor_version(strategy_name)`

创建价格因子模拟器版本目录。

**参数**：
- `strategy_name` (str): 策略名称

**返回**：
- `(version_dir, version_id)`: 版本目录路径和版本ID

**示例**：
```python
version_dir, version_id = VersionManager.create_price_factor_version(
    strategy_name="example"
)
```

#### `resolve_price_factor_version(strategy_name, version_spec)`

解析价格因子模拟器版本目录。

**参数**：
- `strategy_name` (str): 策略名称
- `version_spec` (str): 版本标识符（`"latest"` 或具体版本号）

**返回**：
- `(version_dir, version_id)`: 版本目录路径和版本ID

**示例**：
```python
# 使用最新版本
version_dir, version_id = VersionManager.resolve_price_factor_version(
    strategy_name="example",
    version_spec="latest"
)
```

### 资金分配模拟器版本管理

#### `create_capital_allocation_version(strategy_name)`

创建资金分配模拟器版本目录。

**参数**：
- `strategy_name` (str): 策略名称

**返回**：
- `(version_dir, version_id)`: 版本目录路径和版本ID

**示例**：
```python
version_dir, version_id = VersionManager.create_capital_allocation_version(
    strategy_name="example"
)
```

#### `resolve_capital_allocation_version(strategy_name, version_spec)`

解析资金分配模拟器版本目录。

**参数**：
- `strategy_name` (str): 策略名称
- `version_spec` (str): 版本标识符（`"latest"` 或具体版本号）

**返回**：
- `(version_dir, version_id)`: 版本目录路径和版本ID

**示例**：
```python
# 使用最新版本
version_dir, version_id = VersionManager.resolve_capital_allocation_version(
    strategy_name="example",
    version_spec="latest"
)
```

### 通用机会池版本解析

#### `resolve_sot_version(strategy_name, sot_version)`

解析机会池（枚举器）版本目录（通用方法）。

这是 `resolve_enumerator_version` 的包装方法，提供统一的接口。返回子目录路径而不是基础目录路径，便于直接使用。

**参数**：
- `strategy_name` (str): 策略名称
- `sot_version` (str): 机会池版本标识符（兼容旧命名）

**返回**：
- `(version_dir, sub_dir)`: 版本目录路径和子目录路径（test/ 或 pool/）

**示例**：
```python
# 通用接口
version_dir, sub_dir = VersionManager.resolve_sot_version(
    strategy_name="example",
    sot_version="latest"
)
```

## 📁 目录结构

```
app/userspace/strategies/{strategy_name}/results/
├── opportunity_enums/          # 枚举器结果
│   ├── test/                   # 测试版本（采样模式）
│   │   ├── meta.json
│   │   └── {version_id}_{timestamp}/
│   └── sot/                    # 枚举输出版本（完整枚举）
│       ├── meta.json
│       └── {version_id}_{timestamp}/
├── simulations/
│   └── price_factor/           # 价格因子模拟器结果
│       ├── meta.json
│       └── {version_id}_{timestamp}/
└── capital_allocation/          # 资金分配模拟器结果
    ├── meta.json
    └── {version_id}_{timestamp}/
```

## 🔄 使用流程

### 枚举器使用示例

```python
from app.core.modules.strategy.managers.version_manager import VersionManager

# 1. 创建版本目录
version_dir, version_id = VersionManager.create_enumerator_version(
    strategy_name="example",
    use_sampling=False  # 完整枚举
)

# 2. 执行枚举逻辑...
# ... 保存机会数据到 version_dir ...

# 3. 后续使用：解析版本目录
version_dir, base_dir = VersionManager.resolve_enumerator_version(
    strategy_name="example",
    version_spec="latest"
)
```

### 价格因子模拟器使用示例

```python
from app.core.modules.strategy.managers.version_manager import VersionManager

# 1. 解析依赖的机会池版本
sot_version_dir, _ = VersionManager.resolve_sot_version(
    strategy_name="example",
    sot_version="latest"
)

# 2. 创建模拟器版本目录
sim_version_dir, sim_version_id = VersionManager.create_price_factor_version(
    strategy_name="example"
)

# 3. 执行模拟逻辑...
# ... 保存结果到 sim_version_dir ...
```

### 资金分配模拟器使用示例

```python
from app.core.modules.strategy.managers.version_manager import VersionManager

# 1. 解析依赖的机会池版本
sot_version_dir, _ = VersionManager.resolve_sot_version(
    strategy_name="example",
    sot_version="latest"
)

# 2. 创建模拟器版本目录
sim_version_dir, sim_version_id = VersionManager.create_capital_allocation_version(
    strategy_name="example"
)

# 3. 执行模拟逻辑...
# ... 保存结果到 sim_version_dir ...
```

## ✅ 优势

1. **代码复用**：消除了各组件中重复的版本管理代码
2. **统一接口**：所有组件使用相同的版本管理接口，降低学习成本
3. **易于维护**：版本管理逻辑集中管理，修改和扩展更容易
4. **类型安全**：使用类型提示，提高代码质量
5. **向后兼容**：提供 `resolve_sot_version` 方法作为向后兼容接口

## 🔍 实现细节

### 设计原则

- **静态方法**：所有方法都是静态方法，无需实例化，高效且线程安全
- **统一格式**：所有版本目录使用统一的命名格式 `{version_id}_{timestamp}`
- **立即更新**：创建版本目录后立即更新 `meta.json`，不依赖后续流程是否成功
- **错误处理**：提供清晰的错误信息，便于调试

### 版本ID管理

版本ID从 1 开始，每次创建新版本时自动递增。`meta.json` 文件记录下一个版本ID，确保版本ID的唯一性和连续性。

## 📝 使用说明

### 导入方式

```python
from app.core.modules.strategy.managers.version_manager import VersionManager
```

### 返回值顺序

- `create_*_version` 方法返回 `(version_dir, version_id)`
- `resolve_sot_version` 方法返回 `(version_dir, sub_dir)`，其中 `sub_dir` 是 `test/` 或 `pool/` 子目录
- `resolve_enumerator_version` 方法返回 `(version_dir, base_dir)`，其中 `base_dir` 是基础目录路径

## 🐛 常见问题

### Q: 版本目录已存在怎么办？

A: `VersionManager` 会在创建版本目录时自动检查并创建必要的父目录。如果版本目录已存在，会直接使用，不会覆盖。

### Q: 如何查找所有版本？

A: 可以使用 `resolve_*_version` 方法配合 `"latest"` 参数查找最新版本。如果需要查找所有版本，可以遍历版本目录下的所有子目录。

### Q: 版本ID会重复吗？

A: 不会。`VersionManager` 通过 `meta.json` 文件管理版本ID，确保每个版本都有唯一的ID。

### Q: 可以手动修改 meta.json 吗？

A: 可以，但不推荐。手动修改可能导致版本ID冲突。如果必须修改，请确保版本ID的唯一性和连续性。

## 📚 相关文档

- [Strategy 模块架构设计](../../ARCHITECTURE_DESIGN.md)
- [Setting Management README](../components/setting_management/README.md)
