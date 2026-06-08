# Decision 002: 策略 Meta 结构与递归发现

## Status

Accepted（2026-06-08）

## Context

策略 `settings.py` 存在以下问题：

1. **身份字段混乱**：根级 `name` 同时承担技术 ID 与中文展示名；列表 API 使用文件夹名，而 `settings.name` 可能是中文，用户难以对应。
2. **信息不足以快速理解策略**：单一 `description` 过于笼统；入场逻辑写在 `strategy_worker.py` 与 `core` 中，缺少面向用户与 AI 的结构化说明。
3. **发现逻辑过粗**：仅扫描 `strategies/` 一层目录；无法按文件夹分组；不校验路径合法性。
4. **与 Tag 心智不一致**：Tag 已有 `display_name` 等展示字段，策略应对齐，便于同一批用户维护。

后续将引入 AI 辅助理解策略，需要稳定、可读的 meta 块；**不要求兼容旧版 settings 平铺格式**，新逻辑先行，下游逐步适配。

## Decision

### 1. 策略权威 ID（`name`）由系统自动生成，不暴露给用户

- **`name`** = 策略目录相对于 `userspace/strategies/` 的**相对路径**（POSIX 风格，用 `/` 分隔）。
  - 示例：目录 `userspace/strategies/momentum/rsi_oversold/` → `name = "momentum/rsi_oversold"`。
- 用户**不在** `settings` 中填写或编辑 `name`；发现（discovery）时根据路径写入 `DiscoveredStrategy.name`。
- `PathManager.strategy(name)` 继续适用：`strategies_root / name`。
- **重命名或移动文件夹 = 更换策略 ID**（API、CLI、结果路径、书签均随之变化）；在文档中说明，不提供隐式别名。

### 2. 用户可见配置：`meta` 嵌套块 + 顶层 `is_enabled`

`settings.py` 身份与文档相关字段收拢如下（**不含 `name`**）：

```python
settings = {
    "is_enabled": True,   # 唯一留在顶层的「开关」类身份字段

    "meta": {
        "display_name": "RSI超跌反弹",   # 必填；human-readable，仅用于展示
        "description": "...",           # 可选；空则 validation warning
        "keywords": [],                 # 可选；字符串列表，分类/检索/AI，默认 []
        "details": {                    # 可选；整块可省略
            "entry": [                  # 可选；字符串列表，描述何时入场
                "RSI(14) 低于超卖阈值（见 core.rsi_oversold_threshold）",
            ],
        },
    },

    # 执行配置仍在顶层，不属于 meta
    "core": { ... },
    "data": { ... },
    "goal": { ... },
    "sampling": { ... },
    # ...
}
```

约定：

| 字段 | 必填 | 说明 |
|------|------|------|
| `meta.display_name` | 是 | 列表、工作台标题等展示用 |
| `meta.description` | 否 | 一两句话摘要 |
| `meta.keywords` | 否 | `List[str]` |
| `meta.details` | 否 | 仅含 `entry: List[str]`；不写不影响加载与运行 |
| `meta.details.entry` | 否 | 用户描述入场条件；**出场条件不从 meta 维护** |

**出场（exit）展示**：由展示层根据 `goal`（`stop_loss` / `take_profit` / `expiration` 等）解析生成，不写入 `meta.details`。

`core` 从 meta 中拆出，留在根级（策略可执行参数，非文档）。

### 3. 递归发现规则

从 `userspace/strategies/` **递归**扫描目录树：

1. 目录名以 `_` 开头 → **跳过**（该目录及其子树是否继续扫描：跳过该目录，不进入；与现有一致）。
2. 某目录**同时**存在 `settings.py` 与 `strategy_worker.py` → 候选策略目录。
3. 计算 `name = relative_path.as_posix()`（相对 `strategies_root`）。
4. **路径合法性**：`name` 的每一段（每个目录名）须满足 machine-readable：
   - 正则：`^[a-zA-Z][a-zA-Z0-9_]*$`（字母开头；仅 ASCII 字母、数字、下划线）。
   - 不满足 → **记录 warning，拒绝注册该策略**（不进入 discovered 集合）。
5. 加载 `settings` 与 worker（嵌套路径使用**按文件加载**，不依赖 `userspace.strategies.{flat}.settings` 式 import 路径）。
6. `StrategySettings.validate()` critical 失败 → 拒绝注册。
7. 父目录仅有子目录、无 `settings.py` + `strategy_worker.py` → **分组目录**，不是策略。

分组示例：

```
userspace/strategies/
└── momentum/                 # 分组（无 settings + worker）
    └── rsi_oversold/         # 策略；name = "momentum/rsi_oversold"
        ├── settings.py
        └── strategy_worker.py
```

同一分组下可有多个策略；**不同分组下允许相同的叶子文件夹名**（因 `name` 含完整路径）。

### 4. 与 Tag 的对齐方向（本决策仅约束 Strategy；Tag 后续跟进）

Strategy 与 Tag 共用同一套 **`meta` 用户字段**（`display_name`、`description`、`keywords`、`details.entry`），且 **系统生成路径型 `name`**、用户不填写。Tag 模块在后续版本中按本决策对齐。

### 5. 实现策略：不兼容旧格式

- **不提供**旧版根级 `name` / `description` 平铺的读取 fallback。
- 先实现新 discovery + `StrategyMetaSettings` 解析逻辑，再改 catalog API、BFF 路由、前端、example 策略等下游。
- `enum_signature_hash` 等执行指纹**不包含** `display_name` / `keywords` / `description` / `details`（纯文档字段）。

### 6. API 与路由

- 列表项 `name` 字段为系统路径 ID（如 `momentum/rsi_oversold`）；另返回 `display_name` 等 meta 字段供展示。
- BFF / 前端路由须支持 **path 型** `strategy_name`（如 Flask `<path:strategy_name>`；React splat `*`）。
- 列表主展示列使用 `display_name`；路径 ID 可作为副信息（tooltip / 次要列），不必作为用户编辑项。

## Rationale

1. **路径即 ID**：天然唯一；无需用户维护全局唯一短名；无需 `name → folder` 注册表；`PathManager` 直接可用。
2. **用户零负担**：不必理解 key 与 display name 区别；中文只写在 `display_name`。
3. **分组自由**：目录结构表达分类；叶子名可重复。
4. **拒绝非法路径**：非 machine-readable 路径段会导致 URL/CLI/import 困难，发现阶段拒绝比运行时失败更安全。
5. **`details.entry` 可选**：实验阶段用户可不维护；exit 由 `goal` 派生，避免双处维护。

## Consequences

### 必须修改的下游（按实现顺序）

1. `StrategyMetaSettings` / `StrategySettings`：嵌套 `meta` 解析；`is_enabled` 顶层；`core` 根级。
2. `StrategyDiscoveryHelper`：递归扫描、路径校验、文件加载 worker/settings。
3. `DiscoveredStrategy`：`name` 为相对路径；保留 `folder`（绝对路径）。
4. `workbench_catalog._summary()`：返回 `display_name`、`keywords`、`description` 等。
5. `strategy_runtime.py`：去除扁平 `importlib` 路径假设。
6. BFF routes、React router、`strategyApi.js`：path 型 strategy name。
7. `setup/init_userspace` 下 example 策略与 `settings_example.py`。
8. 相关测试与模块 `CHANGELOG`。

### 明确不做（本决策范围内）

- 旧 settings 平铺格式的自动迁移或双读。
- `meta.details.exit`（由 `goal` 展示层解析）。
- 文件夹重命名时的 ID 别名或自动重定向。
- 本决策内 Tag 模块代码改动（仅记录对齐方向）。

### 风险与运维提示

- 用户若用中文或空格命名文件夹，策略将无法被发现（warning + skip）；文档须说明：**文件夹路径段用英文/下划线，中文放在 `display_name`**。
- 移动策略目录后，历史 `results/`、DB 快照中的 `strategy_name` 不会自动跟随，需用户自行处理或重新跑（与「文件夹即 ID」语义一致）。

## Alternatives Considered

| 方案 | 放弃原因 |
|------|----------|
| 用户填写 `meta.name` = 叶子文件夹名，全局唯一 | 限制分组下同名策略；需额外 path 注册表；用户多填一项易错 |
| 用户填写 `meta.name` = 相对路径 | 与文件夹易不一致；重复维护 |
| 保留根级 `name` 兼作展示名 | 中文用户无法用英文 key 交流；与列表展示错位 |
| 路径非法仅 warning 仍注册 | URL/CLI 不可靠 |
| `details` 含 `exit` | 与 `goal` 重复维护；exit 可自动解析 |

## References

- 讨论定稿：策略工作台 meta 增强与发现逻辑（2026-06-08）
- Tag 模块 `display_name` 先例：`core/modules/tag/models/scenario_model.py`
- 现有发现实现：`core/modules/strategy/services/discovery/discovery.py`
