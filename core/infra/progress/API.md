# Progress API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.6.0`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**；内部私有实现不写入。  
> **位置（硬性）：** 模块根目录 `API.md`。  
> **测试（硬性）：** 所列公开入口必须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Progress`。节点类型从 [`contracts.py`](./contracts.py) 导入，或经 `Progress.types`。

---

## Progress

**描述：** 进度文件的门面（静态 API，勿实例化）

### start

`Progress.start(node_id: str, *, job: str = "", label: str = "", weight: float = 1, steps: Sequence[Mapping] | None = None) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 创建或覆盖一棵进度树。根节点为 running，子节点为 pending
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 根节点 id。作为文件名，不能含路径分隔符 |
| job | str | （可选）任务种类，默认空字符串 |
| label | str | （可选）显示名，默认空字符串 |
| weight | float | （可选）权重，默认 1 |
| steps | Sequence[Mapping] \| None | （可选）子节点。每一项也是进度节点，至少含 id |

- **返回值：** `None`
- **错误与异常：** id 无效、id 与另一份文件冲突、steps 不是列表时抛出 `ValueError`
- **举例：**

```python
Progress.start(
    "run-1",
    job="renew",
    label="更新数据",
    steps=[
        {"id": "run-1:list", "label": "股票列表"},
        {"id": "run-1:daily", "label": "日线", "weight": 3},
    ],
)
```

### tick

`Progress.tick(node_id: str, done: int, total: int, *, source: str | None = None, label: str | None = None, detail: str | None = None, log: bool = True) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 更新一个叶子节点的计数，并把该节点标为 running。调用一次更新一次，并打一行日志
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 叶子节点 id |
| done | int | 已完成数量 |
| total | int | 总数量 |
| source | str \| None | （可选）当前项。不传则不改 |
| label | str \| None | （可选）显示名。不传则不改 |
| detail | str \| None | （可选）说明。不传则不改。有内容且 log 为真时，这行文字就是日志 |
| log | bool | （可选）是否打印日志，默认 True |

- **返回值：** `None`
- **错误与异常：** 节点不存在时抛出 `FileNotFoundError`。节点还有子节点、或计数不是非负整数时抛出 `ValueError`
- **举例：**

```python
Progress.tick("run-1:daily", 4, 10, source="daily", detail="抓取 4/10")
```

### finish

`Progress.finish(node_id: str) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 把这个节点标成完成，ratio 为 1。不改其它节点的状态
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 节点 id |

- **返回值：** `None`
- **错误与异常：** 节点不存在时抛出 `FileNotFoundError`
- **举例：**

```python
Progress.finish("run-1:list")
```

### fail

`Progress.fail(node_id: str, detail: str = "") -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 把这个节点标成失败。父节点保持原状态，并把这一档权重计进父节点
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 节点 id |
| detail | str | （可选）失败说明。空字符串则不改原说明 |

- **返回值：** `None`
- **错误与异常：** 节点不存在时抛出 `FileNotFoundError`
- **举例：**

```python
Progress.fail("run-1:daily", detail="日线失败")
```

### cancel

`Progress.cancel(node_id: str, detail: str = "") -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 把这个节点标成取消。ratio 停在原地
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 节点 id |
| detail | str | （可选）取消说明。空字符串则不改原说明 |

- **返回值：** `None`
- **错误与异常：** 节点不存在时抛出 `FileNotFoundError`
- **举例：**

```python
Progress.cancel("run-1", detail="已取消")
```

### pause

`Progress.pause(node_id: str) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 暂停这个节点。计数和 ratio 不动
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 节点 id |

- **返回值：** `None`
- **错误与异常：** 节点不存在时抛出 `FileNotFoundError`
- **举例：**

```python
Progress.pause("install")
```

### resume

`Progress.resume(node_id: str) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 把暂停的节点恢复为 running
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 节点 id |

- **返回值：** `None`
- **错误与异常：** 节点不存在时抛出 `FileNotFoundError`
- **举例：**

```python
Progress.resume("install")
```

### clear

`Progress.clear(node_id: str) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 删除包含该节点的那份根文件
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 节点 id。可以是根，也可以是其中一层 |

- **返回值：** `None`
- **错误与异常：** 节点不存在时抛出 `FileNotFoundError`
- **举例：**

```python
Progress.clear("run-1")
```

### read

`Progress.read(node_id: str) -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 读取包含该节点的整份根文件。解析器使用其中的 ratio、status、label、detail。没有则返回 None
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| node_id | str | 节点 id |

- **返回值：** `dict | None` — 根节点。字段见 `ProgressNode`
- **举例：**

```python
root = Progress.read("run-1:daily")
```

### latest

`Progress.latest(job: str) -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 返回这个 job 里 updated_at 最新的根文件。没有则返回 None
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| job | str | 任务种类，与 start 时的 job 一致 |

- **返回值：** `dict | None` — 根节点
- **举例：**

```python
current = Progress.latest("renew")
```

### types

**描述：** `ProgressNode`

---

## ProgressNode

**描述：** 进度节点的字段。根和 steps 里的每一项相同。

| 名字 | 类型 | 说明 |
|------|------|------|
| id | str | 节点 id |
| job | str | 任务种类 |
| status | str | pending、running、paused、completed、failed、cancelled |
| source | str | 当前项 |
| label | str | 显示名。空字符串表示不展示 |
| detail | str | 说明。空字符串表示不展示 |
| weight | float | 相对同级的权重 |
| done | int | 叶子是已完成数；有子节点时是已结束的子节点数 |
| total | int | 叶子是总数；有子节点时是计入权重的子节点数 |
| ratio | float | 0 到 1 |
| started_at | int | 开始时间。未开始为 0 |
| updated_at | int | 最近更新时间。未更新为 0 |
| steps | list | 子节点，结构与本节点相同 |
