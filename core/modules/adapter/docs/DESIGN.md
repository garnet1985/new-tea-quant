# Adapter 设计说明

**版本：** `0.2.0`

本文档说明 **userspace 扩展布局**、**动态加载规则**、**`process` 上下文**，以及与 **`AdapterDispatcher`** 的协作关系。实现以 `base_adapter.py`、`adapter_validator.py`、`core/modules/strategy/components/scanner/adapter_dispatcher.py` 为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## userspace 目录约定

每个 adapter 占一个与名称一致的子目录：

```text
userspace/adapters/
├── console/
│   ├── adapter.py      # 必须：实现继承 BaseOpportunityAdapter 的类
│   └── settings.py     # 可选：顶层变量 settings 或 config（dict）
└── <adapter_name>/
    ├── adapter.py
    └── settings.py
```

- **模块路径**：`userspace.adapters.<adapter_name>.adapter`（与目录名一致）。
- **类查找**：加载模块后取 **第一个** 满足「继承 `BaseOpportunityAdapter` 且非基类本身」的类；验证器与分发器使用相同规则。
- **配置**：`BaseOpportunityAdapter._load_config` 导入 `userspace.adapters.<adapter_name>.settings`，读取模块级 **`settings`** 或 **`config`**；缺失则为 `{}`。

---

## 策略配置

在策略的 **scanner** 段使用 **`adapters`**：

- 类型：字符串（单个名）或字符串列表；空或缺省时等价于仅依赖分发器侧的「无配置」分支（使用 `default_output`）。
- 默认占位：解析逻辑会将缺省补为 `["console"]`（见 `ScannerSettings`），具体以策略设置代码为准。

校验：`ScannerSettings._validate_adapters` 对列表中每个名称调用 **`validate_adapter(name)`**，失败则写入校验报告并提示检查 `userspace/adapters/<name>/adapter.py`。

---

## `process` 与上下文

```text
process(opportunities: List[Opportunity], context: Dict[str, Any]) -> None
```

**`context`** 由 Scanner 管线传入，常见键包括：

| 键 | 说明 |
| --- | --- |
| `date` | 扫描日期 |
| `strategy_name` | 策略名 |
| `scan_summary` | 扫描汇总（如股票数等，依实现而定） |

`Opportunity` 为策略模块定义的数据类；adapter 不应修改框架扫描语义，仅消费数据。

---

## 运行时行为（AdapterDispatcher）

1. **`adapter_names` 为空**：直接调用 **`BaseOpportunityAdapter.default_output`**，不再加载 userspace。
2. **非空**：按顺序对每个名称 `importlib.import_module("userspace.adapters.{name}.adapter")`，取第一个合法子类，**无参实例化**后调用 **`process`**。
3. **任一成功**即增加成功计数；若**全部**加载失败或 `process` 抛错导致成功数为 0，则 **`default_output`**。
4. 单个 adapter 失败会记录错误日志并继续尝试下一个。

---

## HistoryLoader 与结果目录

`HistoryLoader` 通过 **`VersionManager.resolve_price_factor_version(..., version_spec="latest")`** 定位模拟版本目录，再用 **`ResultPathManager`** 解析单股 JSON 与会话汇总文件。无文件或解析失败时返回 **`None`**，调用方需容错。

统计字段含义见 `HistoryLoader.load_stock_history` 文档字符串；ROI / `result` / `duration_in_days` 等来自价格模拟落盘格式。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API.md](API.md)

---

## 设计决策（原 DECISIONS.md）

# Adapter 设计决策

**版本：** `0.2.0`

---

## 决策 1：userspace 包路径与目录名一致

**背景（Context）**  
需要在不修改 core 的前提下扩展「扫描完成后」的行为。

**决策（Decision）**  
约定 `userspace/adapters/<name>/adapter.py`，导入路径为 `userspace.adapters.<name>.adapter`；策略配置里只写 `<name>`。

**理由（Rationale）**  
与数据源、策略等 userspace 扩展方式一致，且可用标准 `importlib` 加载。

**影响（Consequences）**  
目录名即公开标识符，重命名 adapter 需同步改配置。

**备选方案（Alternatives）**  
在配置中写完整模块路径：更灵活但更冗长，当前未采用。

---

## 决策 2：模块内第一个合法子类即实现

**背景（Context）**  
同一 `adapter.py` 可能定义多个类，`inspect.getmembers` 顺序不保证直观。

**决策（Decision）**  
`validate_adapter` 与 `AdapterDispatcher._load_adapter_class` 均取 **第一个** 满足「继承 `BaseOpportunityAdapter` 且非基类」的类。

**理由（Rationale）**  
实现简单，且鼓励每个 adapter 文件只放一个主实现类。

**影响（Consequences）**  
多子类并存时行为依赖枚举顺序；扩展点文档要求「单主类」。

**备选方案（Alternatives）**  
约定类名后缀或显式注册表；未实现以保持加载逻辑最小。

---

## 决策 3：HistoryLoader 放在 adapter 包内

**背景（Context）**  
控制台等 adapter 需要展示历史模拟统计。

**决策（Decision）**  
提供 **`HistoryLoader`** 静态工具类，内部依赖 **`modules.strategy`** 的版本与路径管理器读取 JSON。

**理由（Rationale）**  
与「展示侧」常见需求放在一起，避免每个 userspace adapter 重复解析路径。

**影响（Consequences）**  
`modules.adapter` 对 `modules.strategy` 存在硬依赖；无策略结果时方法返回 `None`，调用方需容错。

**备选方案（Alternatives）**  
将加载逻辑完全迁入 `strategy` 或独立 `results` 子模块；当前以复用现有结果布局为主。

---

## 决策 4：分发与兜底放在 strategy.Scanner

**背景（Context）**  
扫描管线末尾需要统一调用 adapter。

**决策（Decision）**  
运行时调度由 **`AdapterDispatcher`**（strategy 包）实现；全部失败或无配置时调用 **`BaseOpportunityAdapter.default_output`**。

**理由（Rationale）**  
Scanner 已持有机会列表与上下文，避免在 `modules.adapter` 再引一层编排。

**影响（Consequences）**  
阅读「端到端行为」需同时看 strategy 的 dispatcher 与本模块基类。

**备选方案（Alternatives）**  
将 `AdapterDispatcher` 迁入 `modules.adapter`：会减少 strategy 体积，但会加深 adapter 对扫描管线的依赖，当前未采用。

