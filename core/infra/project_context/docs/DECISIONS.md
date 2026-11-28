# Project Context — 设计与决策

**模块：** `infra.project_context` · **版本：** `0.2.2`

**最低支持核心版本：** `>=0.5.0`

本文记录项目上下文模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

项目上下文模块要解决的问题：全项目的**路径解析与配置访问**散落在各调用方手中，容易产生多入口、命名漂移与字符串路径拼接错误。目标是提供一个单一、静态、跨平台的访问入口，统一处理：

- 项目根 / userspace 根的定位与缓存，支持自定义 userspace 位置与多环境切换；
- 配置的加载与覆盖（core 默认值 ∪ userspace 覆盖 ∪ 环境变量），区分"可选配置"与"强依赖配置"的缺失语义；
- 公开面保持窄：内部实现（PathManager / ConfigManager / DiscoveryManager）不对外暴露。

约束与上下文：路径需跨 Windows / macOS / Linux 工作，且原生支持中文与空格路径；公开契约要单一真源、有测试覆盖。

## 方案与思路

整体走 **Facade + 静态 namespace** 路线：包根只导出 `ProjectContext` 作为静态 namespace 容器（无实例状态），内部 Manager 不对外导出；人读契约收敛到根目录 `API.md` 一份，跨模块类型放在 `contracts.py` 并经 `ProjectContext.types` 挂载。

**路径解析：**

- 项目根自包路径向上查找根标记（`.git`、`pyproject.toml` 等），命中后缓存；否则 fallback 父链。
- userspace 根按固定优先级链解析：`NEW_TEA_QUANT_USERSPACE_ROOT` → `NTQ_USERSPACE_ROOT` → `{project_root}/.ntq/userspace-path.json` → `{project_root}/userspace`；已配置路径不要求目录已存在，但禁止静默回落。
- 安装校验与运行时读取分离：`resolve_userspace_target(raw)`（仅安装 / precheck）做 `expanduser().resolve()` + 可写性检查，失败抛错且不写坏 json；空 `raw` 沿用已有 json。运行时只用 `get_userspace_root`，不另设近义别名；其余命名维持 `get_xxx_root` / `get_xxx_directory` / `get_xxx_path`。
- `coerce_strategy_folder`：绝对 discovered folder 原样返回；相对 id 拼到 `userspace/strategies/`。
- 所有路径 API 返回 `pathlib.Path` 而非字符串。

**配置加载与发现：**

- `load_core_config` 委托 `DiscoveryManager.load_overridable_config("", name)`，缺文件返回空 dict；`load_database_config` 合并 `database/common` + `database/{type}` + userspace + `DB_*` env；`load_data_config` 及访问器读合并后的 `data.json` 字段。
- `discover_configs(domain)` 取 core ∪ userspace 下 id 并集排序；`load_overridable_config` 默认 `ConfigManager.load_with_defaults`，可注入自定义 `merge_fn`（如 `merge_market_profile_dicts` 做市场 profile 规则深度合并）。
- 配置缺失按"可选 / 强依赖"分级处理（见下文 DEC-03）。

**测试策略：** `__test__/test_api.py` 做公开 Facade / contracts 契约 smoke（`force_run`）；`core/__test__/` 测内部 Manager 行为。

关键选型（单一入口、路径类型、缺失策略、优先级链、契约载体、find_in_tree 归属）见下文 DEC-01 ～ DEC-06。

---

## DEC-01：单一入口 ProjectContext 静态 namespace

**是什么：** 包根只导出 `ProjectContext`，作为静态 namespace 容器，无实例状态。

**为什么选它：**

- 防止多入口与命名漂移——所有路径与配置访问收敛到一个命名空间下
- 静态调用不需要实例化，与"全局路径/配置"的天然单例属性匹配
- 内部 Manager（PathManager / ConfigManager / DiscoveryManager）不对外导出，保持公开面窄

**放弃了什么：**

- **多实例依赖注入：** 每个调用方各自 `ProjectContext()` — 路径与配置本质是项目级单例，多实例只会带来状态分叉
- **函数式 API：** 顶层一组 `get_xxx()` 函数 — 没有 namespace 收敛，调用方 import 面过宽

---

## DEC-02：路径返回类型用 pathlib.Path

**是什么：** 所有 `get_xxx_root` / `get_xxx_directory` / `get_xxx_path` 返回 `pathlib.Path`，不返回字符串。

**为什么选它：**

- 跨平台路径拼接（Windows / macOS / Linux）由 pathlib 统一处理
- `Path` 对象可继续组合（`/`、`joinpath`、`with_name`），不会在调用方散落字符串拼接
- 中文 / 空格路径经 pathlib 原生支持

**放弃了什么：**

- **返回字符串：** 调用方需要时再 `str()` — 字符串拼接易错（分隔符、尾斜杠），丧失类型信息

---

## DEC-03：配置缺失策略分级处理

**是什么：** `load_core_config` 缺文件返回 `{}`（温和失败）；`load_overridable_config` 在 core 与 userspace 两侧皆无时抛 `OverridableConfigNotFoundError`（显式失败）。

**为什么选它：**

- 可选配置（如某个模块的专属 json）允许不存在，返回空 dict 让调用方走默认
- 强依赖的可覆盖配置（如 database/common）必须存在，否则静默继续会导致难排查的运行时错误
- 两种语义分开，避免一刀切

**放弃了什么：**

- **一律返回空：** 强依赖配置缺失时静默继续，调用方拿到 `{}` 后行为未定义
- **一律抛错：** 可选配置也得先建空文件才能跑，上手成本高

---

## DEC-04：userspace 路径优先级链固定

**是什么：** userspace 根目录按 `NEW_TEA_QUANT_USERSPACE_ROOT` → `NTQ_USERSPACE_ROOT` → `{project_root}/.ntq/userspace-path.json` → `{project_root}/userspace` 顺序解析；已配置路径不要求目录已存在，但禁止静默回落。

**为什么选它：**

- 环境变量优先级最高，便于测试与多环境切换
- `userspace-path.json` 支持安装时自定义路径
- 默认 `{project_root}/userspace` 让开箱即用场景零配置
- 已配置路径不静默回落——若显式配置了路径但目录不存在，应当显式报错而非悄悄用默认路径

**放弃了什么：**

- **仅默认路径：** 不支持自定义 userspace 位置 — 多项目并存与 CI 场景受限
- **配置文件任意位置：** 支持任意配置文件指定 — 解析链过长，排查困难

---

## DEC-05：契约载体 = API.md + test_api.py

**是什么：** 人读 API 契约只维护根目录 `API.md` 一份，与 `__test__/test_api.py` 成对；不再维护 `api.yaml`。

**为什么选它：**

- 单一真源避免多份文档漂移
- `test_api.py` 强制公开 API 有测试覆盖
- Markdown 对人读友好，yaml 冗余

**放弃了什么：**

- **api.yaml 机器可读契约：** 机器校验可自动化 — 当前阶段机器校验收益低于维护成本

---

## DEC-06：find_in_tree 放在 infra.discovery

**是什么：** 文件树扫描工具 `find_in_tree` 由 `infra.discovery` 提供，project_context 不自带。

**为什么选它：**

- 通用文件 IO 与"项目上下文"解耦——discovery 是通用扩展扫描，project_context 专注路径与配置
- 避免 project_context 承担过多职责

**放弃了什么：**

- **project_context 自带 find_in_tree：** 调用方少 import 一层 — 职责越界，长期会成为杂货铺

---

## DEC-07：数据包类型与会员文件名进 contracts

**是什么：** `DATA_PACKAGE_KINDS`、`MEMBERSHIP_TOKEN_FILE_NAME` 放在 `contracts.py`（并挂 `ProjectContext.types`）；setup / membership 经 contracts 或 Facade 取用，生产代码不再深导入 `PathManager` 仅为常量。

**为什么选它：** 消除「读一个元组就必须穿透 PathManager」；membership 已依赖 project_context，文件名可单真源。

**影响：** 不在 `PathManager` 上留兼容别名；测试侧 PathManager mock 逐步改 Facade（backlog）。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
