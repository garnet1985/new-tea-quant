# Project Context — 决定

**版本：** `0.2.0`

本文列出项目上下文模块的关键选型回顾。  
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

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

## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
