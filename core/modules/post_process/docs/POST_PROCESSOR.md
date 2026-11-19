# 后续处理（PostProcess）

**模块：** `modules.post_process` · **版本：** `0.3.2`

**最低支持核心版本：** `>=0.5.0`

**状态：** 已落地（`modules.post_process` 0.3.2）  

扫描结果经 adapter 规范化为 [`ScanSessionReport`](./PROTOCOL.md) 之后，交给用户声明的 **后续处理（PostProcess）**：一组**彼此独立**的 component，各自消费同一份标准协议。

**不是 pipeline：** component 的 output **不会**自动变成下一个的协议 input；标准协议形状不因「串起来」而改变。  
**执行时**可按依赖拓扑得到一个有序序列，逐个调用——那只是调度顺序，不是数据流水线。

---

## 概念

```text
ScanSessionReport          # 标准协议（同一份，只读语义上共享）
        │
        ▼
 PostProcess（key / name）
        │
        ├── component A
        ├── component B     # 声明为无序集合
        └── component C
              │
              ▼
        执行：无 depends_on → 任意稳定顺序逐个跑
             有 depends_on → 拓扑排序后逐个跑
```

| 概念 | 说明 |
|------|------|
| **PostProcess** | 有 `key`（及可选展示名）的后续处理单元；声明用哪些 component |
| **Component** | 真正干活的单元；input 见下节 |
| **标准协议** | 始终是 `ScanSessionReport`（见 [PROTOCOL.md](./PROTOCOL.md)） |
| **依赖产出** | 仅当声明了 `depends_on` 时注入；与协议分开 |

---

## Component 的 input

每个 component 的 input 固定为两路：

1. **标准协议** — `ScanSessionReport`（全员同一份；不因其它 component 改写协议而替换）  
2. **依赖产出** — 它所依赖的 N 个 component 的 return，以 **key → output** 注入（key = component 名）

无 `depends_on` 时，第 2 路为空映射。

建议调用形：

```text
run(session: ScanSessionReport, config: dict, deps: dict[str, Any]) -> Any
```

- `deps`：仅包含本 component 声明依赖的那些 key；未依赖则为 `{}`  
- **返回值**：本 component 的局部产出；框架可缓存，供**依赖了它的**下游注入  
- 返回值 **不是** 下一跳的标准协议；框架**不会**用返回值替换 `session`

局部类型（例如演示用的可交易对象）只活在相关 component 的 return / 内部约定里，**不属于**三层出口协议。

---

## PostProcess 配置

### 策略侧引用

```yaml
scanner:
  # 后续处理不在策略 settings；见 post_processors/<key>.is_enabled
```

### 命名定义与目录（userspace）

用户自定义的 **PostProcess** 与 **Component** 都放在 `userspace/extensions/` 下，由框架**发现 + 按 key 加载**（模式对齐现有 `adapters`）。

```text
userspace/extensions/
├── post_processes/                 # PostProcess 声明（配置）
│   └── <key>.yaml                  # 或 <key>/post_process.yaml
└── components/                     # Component 实现（代码）
    └── <name>/
        ├── adapter.py            # 必须：BaseAdapter 子类
        └── settings.py             # 可选：默认 config
```

| 对象 | 目录 | 导入 / 标识 |
|------|------|-------------|
| PostProcess | `extensions/post_process/post_processors/` | key = 文件名（无后缀）或子目录名 |
| Component | `extensions/post_process/adapters/<name>/` | 模块 `userspace.extensions.post_process.adapters.<name>.component` |

PathManager 提供：`get_post_processors_directory()`、`get_adapters_directory()`。

### 文件形态

```yaml
key: demo_handoff
name: "演示：打印 + 通知 + 假交易"   # 可选，展示用

on_error: continue    # continue | stop（可选，默认 continue）
on_empty: run         # run | skip：会话无机会时是否仍执行（可选）

# 无序声明：用 mapping，不要用 list 表达「流水线」
adapters:
  presenter:
    config:
      print: true
      show_history: true

  msg_sender:
    config:
      dry_run: true
      channel: wecom_webhook
    depends_on:
      - presenter                 # 可选：注入 presenter 的 return

  paper_trader:
    config:
      dry_run: true
    depends_on:
      - presenter
```

要点：

- `components` 是 **map（集合）**，不是有序列表  
- 每个条目：`config`（可选）+ `depends_on`（可选，component 名列表）  
- 未写 `depends_on` = 不依赖其它 component，只需标准协议  

---

## 执行语义

1. Adapter（或等价层）得到并校验 **一份** `ScanSessionReport`  
2. 枚举所有 ``is_enabled: true`` 的 PostProcessor  
3. 对每个 PostProcessor：按 adapters 的 `depends_on` 做 **拓扑排序**  
   - 无边：采用**稳定次序**（例如按 component 名排序），保证可复现，但不赋予「流水线」语义  
   - 有环：配置错误，拒绝执行并报错  
4. 按序逐个调用；每次传入 **同一 `session`** + 当前已缓存的依赖 `deps`  
5. 将每次 `run` 的返回值写入该 component 名下的产出缓存，供后续依赖方使用  
6. `on_error: continue` — 单 component 失败记日志，继续；`stop` — 中止剩余  

**不做的事：** 把 A 的 return 当作 B 的 `session`；不在框架层合并/改写三层协议。

---

## Component 准则

1. **接受标准协议** — 至少能处理 `ScanSessionReport`；需要单策略/单机会时自行从 `strategies` / `opportunities` 向下取。  
2. **默认遵守** 各 `StrategyScanReport.goal`；改止损/止盈/持有等必须用户在自己的 component 里**显式**改。  
3. **依赖产出自管** — `deps[name]` 的形状由被依赖方文档约定；不是全局协议。  
4. **局部协议自管** — 可交易演示等类型不进入 adapter 三层出口。

抽象基类（实现时）只需固定上述 `run(session, config, deps)` 与发现约定，不必做成万能框架。

---

## 全局启用

```yaml
# post_processors/presenter/post_processor.yaml
key: presenter
is_enabled: true
```

策略 `settings.scanner` **不再**配置 post_process；旧字段加载时会被丢弃。

---

## Example adapters（演示用）

跑通与否次要；用于说明组装方式。可作为 ship 在 `userspace/extensions/post_process/adapters/` 的模板，或 initialization 种子。

| 名 | 典型行为 | 常见 return |
|----|----------|-------------|
| `presenter` | 组装会话视图；可选 CLI；加载同策略 price 回测历史 | `{strategies, backtest_history}`（供 UI / `deps`） |
| `email_sender` / `wechat_sender` / `sms_sender` | 通知；建议默认 `dry_run` | 通常 `None` |
| `demo_broker` | 演示下单（easytrader / vnpy / qmt） | 可选下单回执 |

### 扫描页 UI 槽（SPECIAL-CASE，见 DECISIONS DEC-05）

`run_enabled_post_processors` 聚合 adapter outputs 后，若含 `presenter` return，写入扫描 report：

`post_process.ui.scan_report = { view: "presenter", props: <presenter return> }`

FED 写死识别 `view=presenter`：机会明细仍用默认表，有载荷时追加回测列。**本迭代不做**通用模板引擎；第二个 UI adapter 出现时再定契约 + 前端解析引擎。

---

## 发现与加载（可扩展性）

用户只往 userspace 丢目录/YAML，框架必须能 **枚举** 与 **按名解析**，否则 enabled 的 PostProcessor 与 `adapters.presenter` 无法落地。能力对齐现有 `PostProcess.validate_post_processor` / `AdapterLoader`。

### Component 发现

| API（建议） | 行为 |
|-------------|------|
| `list` / `discover` | 扫描 `components/` 下子目录；返回可用 `name` 列表（可附带是否可加载） |
| `load_class(name)` | 导入 `userspace.extensions.post_process.adapters.<name>.component`，取第一个合法 `BaseAdapter` 子类 |
| `validate(name)` | 可加载且实现 `run(session, config, deps)` → `(ok, message)` |

约定与 adapter 相同：**一目录一名；模块内第一个合法子类即实现**。可选 `settings.py` 提供默认 config（可被 PostProcess 里的 `config` 覆盖）。

### PostProcess 发现

| API（建议） | 行为 |
|-------------|------|
| `list` / `discover` | 扫描 `post_processes/`：`*.yaml` 或含声明文件的子目录；返回 `key` 列表 |
| `load(key)` | 读入声明 → 结构化对象（key、components map、on_error…） |
| `validate(key)` | 文件存在、YAML 可解析、`components` 中每个 name 能通过 Component.validate；`depends_on` 无环且引用的 name 都在本 PostProcess 的 components 集合内 |

扫描路径只执行 ``is_enabled: true`` 且 `validate_post_processor` 通过的声明；失效的 enabled 项执行期记错并按 `on_error` 处理。

### 解析流程（执行前）

```text
 list_enabled_post_processors()
        │
        ▼
 for key in enabled:
     PostProcess.load_post_processor(key)
            │
            ▼
     for name in adapters:
         Adapter.validate / load_class(name)
            │
            ▼
     拓扑排序(depends_on) → 依次 run(session, config, deps)
```

### 打包 / 分发

PostProcess 为全局配置，**不随策略 share bundle 导出**。自定义装配放在本机 / 初始化种子的 `userspace/extensions/post_process/`。

## 刻意保持简单的点

- 用户只配：**is_enabled + 用哪些 adapter**（无序）  
- 需要协作时再写 **`depends_on`** → 执行期拓扑 + `deps` 注入  
- 可扩展性靠 **userspace 目录约定 + list/load/validate**，不靠中央注册表  
- 不引入 steps/sinks、协议变换链、并行 DAG 语法（以后若要并行，仍是同一 input 模型上的调度优化）

---

## 相关文档

- [出口协议（三层）](./PROTOCOL.md)  
- [架构](./ARCHITECTURE.md)  
