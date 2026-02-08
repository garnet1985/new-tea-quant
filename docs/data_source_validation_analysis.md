# Data Source 模块存在性检查分析

## 一、问题现象

模块内存在大量「存在性检查」和「类型/结构兜底」，导致：
- 业务逻辑与防御性检查混在一起，可读性差
- 同一检查在多处重复
- 难以区分「合法缺失」与「配置错误」

---

## 二、典型模式统计

| 模式 | handler_helper | base_handler | config |
|------|----------------|--------------|--------|
| `x.get("y") or {}` | 50+ | 20+ | 30+ |
| `if not x` / `if x is None` | 60+ | 40+ | 25+ |
| `hasattr(x, "method")` | 15+ | 5+ | 0 |
| `isinstance(x, dict)` | 20+ | 10+ | 10+ |
| `getattr(x, "attr", None)` | 10+ | 5+ | 0 |

---

## 三、问题分类

### 3.1 config 类型不一致

```python
# handler_helper 里反复出现
config = context.get("config")
if hasattr(config, "get_apis"):
    apis_conf = config.get_apis()
else:
    apis_conf = (config or {}).get("apis", {}) if isinstance(config, dict) else {}
```

**原因**：config 有时是 `DataSourceConfig`，有时是原始 dict，需要双重处理。

**设计原则**：config 在进入主程序前必须已是 `DataSourceConfig` 实例，不接受 dict。入口处强制转换，否则抛错。

---

### 3.2 context 为松散 dict

```python
config = context.get("config")
data_manager = context.get("data_manager")
schema = context.get("schema")
deps = context.get("dependencies") or {}
```

**原因**：context 是 `Dict[str, Any]`，字段可选，每处都要防御性读取。

---

### 3.3 api_conf 结构未固化

```python
params_mapping = api_conf.get("params_mapping") or {} if isinstance(api_conf, dict) else {}
result_mapping = api_conf.get("result_mapping") or {}
```

**原因**：api_conf 来自 dict，结构未在类型上约束，需要 `.get` + 默认值。

**设计原则**：api_conf 必须固化为 `ApiConfig` 等 DataClass，加载时解析并校验。

---

### 3.4 多级嵌套的 fallback

```python
renew = self.get("renew") or {}
last_info = renew.get("last_update_info") or {}
fmt = last_info.get("date_format") or self.get("date_format") or "day"
```

**原因**：配置是嵌套 dict，每层都可能是 None，需要连续 fallback。

**设计原则**：更多确定性，少兼容。用户配置错误即错误，第一时间指出并让用户修正，不添加 fallback 业务逻辑。

---

### 3.5 运行时推断（本应是配置）

```python
# 方法1：从 last_update_map 提取 term
# 方法2：从 apis 名推断 (daily_kline → daily)
# 方法3：默认 {"daily", "weekly", "monthly"}
if not terms_set:
    terms_set = {"daily", "weekly", "monthly"}
```

**原因**：terms 未在 job_execution 中显式配置时，用推断补全，逻辑分散且难维护。

**设计原则**：不允许运行时推断。terms 等必须在 job_execution 中显式配置，缺失即报错。

---

## 四、设计原则汇总

| 项 | 原则 |
|----|------|
| 3.1 config | 进入主程序前必须已是 `DataSourceConfig` 实例，不接受 dict |
| 3.3 api_conf | 必须固化为 `ApiConfig` 等 DataClass |
| 3.4 fallback | 配置错误即错误，第一时间指出，不添加 fallback |
| 3.5 推断 | 不允许运行时推断，terms 等必须显式配置 |

---

## 五、建议：前置验证 + 强类型 DataClass

### 5.1 思路

1. **加载时验证**：config 加载后立即校验并解析为 DataClass，失败则直接抛错
2. **强类型传递**：context、config、api 等用 DataClass 表达，不再用裸 dict
3. **消除重复检查**：验证通过后，后续逻辑假定结构正确，不再做存在性检查
4. **无 fallback**：配置缺失或错误时直接报错，不添加兼容逻辑
5. **无推断**：terms、key 等必须显式配置，不允许运行时推断

### 5.2 可选 DataClass 设计

```python
# 配置加载后解析为
@dataclass
class JobExecutionConfig:
    list: str
    key: Optional[str]
    keys: Optional[List[str]]
    terms: Optional[List[str]]
    merge: Optional[Dict[str, str]]
    # 构造时校验：key/keys 二选一，有 keys 时 terms 必填 等

@dataclass  
class ApiConfig:
    api_name: str
    provider_name: str
    method: str
    max_per_minute: int
    params_mapping: Dict[str, str]  # 默认 {}
    result_mapping: Dict[str, str]  # 默认 {}
    # 构造时校验必填字段

@dataclass
class DataSourceConfig:
    table: str
    save_mode: str
    job_execution: Optional[JobExecutionConfig]
    apis: Dict[str, ApiConfig]
    # 构造时完成整体校验
```

### 5.3 效果

| 当前 | 改造后 |
|------|--------|
| `config.get("renew") or {}` | `config.renew`（构造时已保证） |
| `hasattr(config, "get_apis")` | 统一使用 `DataSourceConfig`，无类型分支 |
| `api_conf.get("params_mapping") or {}` | `api_config.params_mapping` |
| `config and hasattr(config, "has_result_group_by")` | `config.job_execution is not None` |

---

## 六、实施优先级

1. **P0**：config 加载时统一解析为 `DataSourceConfig`，失败则抛错，不再传裸 dict
2. **P1**：`JobExecutionConfig`、`ApiConfig` 等子结构用 DataClass，并在构造时校验
3. **P2**：context 中 `config`、`schema` 等核心字段用强类型，减少 `context.get` 分支
4. **P3**：逐步删除冗余的 `if not`、`isinstance`、`hasattr` 检查

---

## 七、小结

当前存在性检查过多的根本原因是：**config/context 长期以 dict 形式传递，且缺少加载期集中校验**。  
通过「加载时验证 + DataClass 强类型」可以在入口处固化结构，后续逻辑可大幅简化，提高可读性和可维护性。
