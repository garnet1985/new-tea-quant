# Progress API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.6.0`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**；内部私有实现不写入。  
> **位置（硬性）：** 模块根目录 `API.md`。  
> **测试（硬性）：** 所列公开入口必须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Progress`。快照类型从 [`contracts.py`](./contracts.py) 导入，或经 `Progress.types`。

---

## Progress

**描述：** 当前任务进度的门面（静态 API，勿实例化）

### open

`Progress.open(source: str, step_total: int, *, job: str = "") -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 开始一次任务。已完成步骤为 0，子步骤清零
- **参数：**

| 名称 | 类型 | 说明 |
|------|------|------|
| source | str | 正在处理的那一项 |
| step_total | int | 总步骤 |
| job | str | （可选）任务种类，默认空字符串 |

- **返回值：** `None`

### step

`Progress.step(done: int, total: int | None = None, *, source: str | None = None, job: str | None = None) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 写入已经完成的步骤，并清掉子步骤
- **参数：**

| 名称 | 类型 | 说明 |
|------|------|------|
| done | int | 已完成步骤 |
| total | int \| None | （可选）总步骤；不传则沿用已有总数 |
| source | str \| None | （可选）正在处理的那一项 |
| job | str \| None | （可选）任务种类 |

- **返回值：** `None`

### sub

`Progress.sub(done: int, total: int, *, source: str | None = None) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 写入当前步骤里的子步骤。不改变已完成步骤
- **参数：**

| 名称 | 类型 | 说明 |
|------|------|------|
| done | int | 已完成子步骤 |
| total | int | 子步骤总数 |
| source | str \| None | （可选）正在处理的那一项 |

- **返回值：** `None`

### close

`Progress.close() -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 这次任务结束。已完成步骤收到总数，子步骤清零
- **参数：** 无
- **返回值：** `None`

### read

`Progress.read() -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 读取当前进度。没有文件时各数字为 0
- **参数：** 无
- **返回值：** `dict` — `job`、`source`、`step`、`step_total`、`sub`、`sub_total`、`updated_at`

### fraction

`Progress.fraction(step: int, step_total: int, sub: int = 0, sub_total: int = 0) -> float`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 把步骤和子步骤合成 0 到 1 的比例。总步骤为 0 时返回 0
- **参数：**

| 名称 | 类型 | 说明 |
|------|------|------|
| step | int | 已完成步骤 |
| step_total | int | 总步骤 |
| sub | int | （可选）已完成子步骤，默认 0 |
| sub_total | int | （可选）子步骤总数，默认 0 |

- **返回值：** `float` — 0 到 1

### types

**描述：** `ProgressSnapshot`
