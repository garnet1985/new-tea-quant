# <Module Display Name> API 文档

**版本：** `<module.version>`  
**最低支持核心版本：** `<compatible_core_versions>`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**；内部私有实现不写入。  
> **位置（硬性）：** 模块根目录 `API.md`。  
> **测试（硬性）：** 所列公开入口必须有 `__test__/test_api.py` 覆盖。

<!-- 若无则删除对应句 -->
快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。概念见 [CONCEPTS.md](./docs/CONCEPTS.md)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

---

## <ClassName>

**描述：** `<一句话类职责>`

<!-- 若该类无 namespace，删除下一个 ### 整块，把 #### 方法提升为 ### -->

### <namespace>

**描述：** `<该 namespace 的职责；无 namespace 时删除本 ### 整块>`

#### <method_name>

`<ClassName>.<namespace>.<method_name>(<params>) -> <Ret>`

- **类型：** `<instance | classmethod | static>`
- **状态：** `<experimental | beta | stable | deprecated>`
- **引入版本：** `<version>`
- **描述：** `<一句话职责；必要时补一句边界或语义注意>`
- **参数：** 无
- **返回值：** `<Type>` — `<语义>`
- **错误与异常：** `<仅当调用方需要处理时填写；否则删除本行>`
- **举例：**

```python
<最小可运行或可粘贴示例>
```

#### <another_method>

`<ClassName>.<namespace>.<another_method>(<params>) -> <Ret>`

- **类型：** `<instance | classmethod | static>`
- **状态：** `<experimental | beta | stable | deprecated>`
- **引入版本：** `<version>`
- **描述：** `<一句话职责>`
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `<param>` | `<Type>` | `<语义、约束>` |
| `<optional_param>` (可选) | `<Type>` | `<语义；写明默认值>` |

- **返回值：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `<field>` | `<Type>` | `<多字段返回 / dataclass 字段时用表格；单返回值用一行「类型 — 语义」即可>` |

- **举例：**

```python
<example>
```

---

## <AnotherClassOrDataclass>

**描述：** `<公开契约类型 / 另一入口类的一句话职责>`

### <method_or_constructor>

`<Signature(...) -> Ret>`

- **类型：** `<instance | classmethod | static>`
- **状态：** `<experimental | beta | stable | deprecated>`
- **引入版本：** `<version>`
- **描述：** `<一句话>`
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `<field>` | `<Type>` | `<语义>` |
| `<field>` (可选) | `<Type>` | `<默认值与语义>` |

- **返回值：** `<Type>` — `<语义；数据类可写「数据类实例」>`

---

## 填法示例（ProjectContext 风格，定稿后可删本段）

## ProjectContext

**描述：** 项目上下文管理 Facade — path / config / meta / cache / discovery

### path

**描述：** 路径操作 namespace

#### get_project_root

`ProjectContext.path.get_project_root() -> Path`

- **类型：** `static`
- **状态：** `stable`
- **引入版本：** `0.4.0`
- **描述：** 获取项目根目录绝对路径
- **参数：** 无
- **返回值：** `Path` — 项目根目录绝对路径
- **举例：**

```python
root = ProjectContext.path.get_project_root()
```

---

## 填写约定（copy 后可删）

1. **层级**：`## Class` →（可选）`### namespace` → `#### method`；无 namespace 时方法用 `###`。
2. **签名行**：方法标题下必须有一行反引号完整签名，与代码一致。
3. **类型**：只允许 `instance` / `classmethod` / `static`。
4. **状态**：只允许 `experimental` / `beta` / `stable` / `deprecated`。
5. **参数**：无参写 `**参数：** 无`；有参用三列表格；可选参数名字列标 `(可选)`。
6. **返回值**：单值用一行 `类型 — 语义`；多字段再用表格。
7. **测试覆盖**：与 `__test__/test_api.py` + `__test__/TEST_CASES.md` 成对维护。
