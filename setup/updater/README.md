# NTQ Updater（设计约定）

本目录用于存放 **updater 说明与后续入口脚本约定**。用户业务数据在 **`userspace/`**，升级**不覆盖**该目录。

**本文档已固化讨论结论**，并与当前 **`pipeline.py` / `helper.py` 骨架** 对齐；未实现的步骤在文中标明「规划中」。

---

## 1. 目标

| # | 内容 |
|---|------|
| 探测新版本 | **HTTP GET** 远端仓库 **`core/system.json`**（GitHub raw / Gitee raw 互为备份），与本地 **`<repo>/core/system.json`** 的 **`version`** 做 semver 比较。 |
| 升级框架 | 以 **发版 zip + 自带管辖地图** 为真源，**不动** `userspace/` 与用户约定保留路径。 |
| 执行者 | 始终 **`userspace/updater`**；zip 内 **不执行任意未校验脚本**（迁移入口由 updater **spawn 新解释器**调用新 `core` 中的模块）。 |
| 异步探测 | 启动 / 周期探测 **不阻塞**其它请求（后台线程或队列）。 |

规模化后可再引入 CDN、独立 manifest、sha256 表等；当前以 **repo + zip** 为主路径。

---

## 2. 目录分工（建议）

| 路径 | 用途 |
|------|------|
| **`userspace/.ntq/update/`** | 缓存远端 `system.json`、下载的 zip、`inbox/`、staging、日志、lift-out 备份等 |
| **`userspace/updater/`** | 长期 bootstrap：停服、镜像、收尾编排 |

---

## 3. 全局保留名单（永远不删不改）

与「管辖范围」无关，**一律跳过**（可与用户扩展合并）：

- `userspace/`
- `.git/`（若存在）
- `.env`、`.env.*`、`config.ini`、`secrets.json` 等
- `backup/`（若用户曾在根目录使用）
- 可选：`.cursor/`、`.vscode/`、`.idea/`、`backup/` …

**`venv/`、`node_modules`**：**不参与保留为「禁止删除」**——升级收尾会 **删掉再重装**（见 §8）。

可选：**`userspace/.ntq/update/preserve-extra.txt`**（每行一条相对仓库根的路径或 glob）。

---

## 4. 核心算法：以新版 zip 为根基 + **管辖范围地图（managed_scope）**

**每一版发版包自带本版的 `update_plan.json`（或等价文件）**，其中最重要的是 **`managed_scope`**：**相对仓库根的顶层路径列表**（如 `["core","setup"]`）。意义：

- **管辖范围内**：以 **`payload/`（或 `payload_root`）下对应树**为唯一真源，对本地做 **递归镜像**——  
  - zip 有、本地没有 → **创建**  
  - 两边都有 → **新覆盖旧**（除非命中 §6 lift-out）  
  - 本地有、zip 在**该前缀下**没有对应文件 → **删除**（避免新版删掉的文件残留）  
- **管辖范围外**：**不删不改**（用户放在根目录的杂项、`xxx.x` 等），除非日后单独约定。
- **管辖范围随版本变化**：**始终以当前正在安装的「新版」地图为准**，不依赖旧版地图常驻磁盘。

### 4.1 跨版本（例：V1→V3）

仅示意顶层：

- V1：`managed_scope = [A,B,C]`  
- V3：`managed_scope = [A,D]`，zip 内含完整 `payload/A`、`payload/D`

则从任意旧版升到 V3：**在 [A,D] 下镜像** → **A** 整树对齐 V3；**D** 新建；**B、C** 已不再属于管辖 → **删除整个 `B/`、`C/`**（若产品语义是「曾由发行维护的顶层目录，下线即删」）。  
根上不在 map、也不在 `A`/`D` 内的用户文件 → **不动**。

**注意**：若曾允许用户在 **`B/`、`C/`** 下放私有数据，删除会一并删掉——产品需约定「用户数据仅在 `userspace/` 或 map 外根文件」。

### 4.2 与顶层镜像（实现口径）

当前实现为 **以 `managed_scope` 每一项为原子单位**（目录或单文件）：

1. 用 **升级前** 本地 `core/system.json` 中的 `managed_scope` 与 **新版** `update_plan` 对比，删除「旧 map 有、新 map 无」的顶层路径（全局保留名跳过，见 `helper.is_global_preserve_managed_entry`）。  
2. 对 **新版** `managed_scope` 每一项：删除 `repo_root/<项>` 后，从 `staging[/payload_root]/<项>` **整棵或整文件** 覆盖拷贝（`helper.install_managed_items_from_staging`）。

即：在每一项内部仍是 **完整子树对齐**；跨项的增量 diff 不做细粒度文件列表。`payload_root` 为空时表示源在 **staging 仓库根**（与分支 zip 一致）。

---

## 5. 例外路径：lift-out → 全量替换 → 还原

若某路径在管辖逻辑里「不能简单覆盖」，可采用：

1. 将该路径 **拷贝/移动到 map 外安全区**（如 `userspace/.ntq/update/backup-<ts>/`），并 **记录清单**  
2. 对管辖范围执行 **无顾虑镜像**  
3. **按清单还原**

适用于小块例外；**大目录不要搬**——优先把 **`venv`/`node_modules`** 直接删后重装（§8）。

---

## 6. 依赖重装（当前实现）

- **默认不主动删除 `venv/`**：除非该项出现在 `managed_scope` 中并被镜像覆盖。业务上可约定 **不动用户 venv**，以当前产品为准。  
- **命令行重装**：`helper.reinstall_runtime_dependencies_cli(repo_root)`（`pipeline` 模块亦再导出同名符号）：先可选 `pip install -r requirements.txt`，再子进程调用 `setup.ui_runtime.install_ui_runtime(force=True)`（BFF + FED `npm install`）。  
- **环境变量**：`NTQ_UPDATE_SKIP_RUNTIME_REINSTALL`、`NTQ_UPDATE_SKIP_ROOT_REQUIREMENTS` 与现有 `NTQ_PIP_NO_CACHE` 等见 `helper.py` 文档字符串。后续 UI 向导可调用同一接口。

---

## 7. 版本探测（简要）

- **本地**：`core/system.json` → `version`  
- **远端**：同上路径 **raw URL**（分支或 tag）  
- **缓存**：可写入 `userspace/.ntq/update/cache/`，减轻请求频率  

zip 下载 URL：Release 固定命名或由版本号推导；可选后续再加校验和。

---

## 8. 流水线顺序（`run_upgrade_pipeline`，与代码一致）

| 顺序 | 步骤 | 说明 |
|------|------|------|
| 1 | `_download_latest_version_package` | 分支源码 zip → `userspace/.ntq/update/inbox/` |
| 2 | `_extract_zip_to_staging` | 解压至 `staging/current`，`ctx.staging_dir` |
| 3 | `_load_update_plan` | `update_plan.json` 或 staging 内 `core/system.json` |
| 4 | `_kill_running_app` | 环境变量钩子（`NTQ_UPDATE_KILL_CMD` 等），未配置则 no-op |
| 5 | `_backup_exceptions` | lift-out → `lift-out/<UTC>/` + manifest |
| 6 | `_snapshot_core_table_schemas_before_managed_scope` | **在镜像 `managed_scope` 之前** 将当前 `core/tables` 全量 schema 写入 `userspace/.ntq/update/cache/pre_mirror_core_table_schemas.json`，供 DB 迁移 diff 对照「升级前代码期望」（否则 `_update_managed_scope` 后磁盘上的旧版 `schema.py` 可能已不存在）。可选跳过：`NTQ_UPDATE_SKIP_SCHEMA_SNAPSHOT=1` |
| 7 | `_update_managed_scope` | 删 obsolete 顶层项 + 从 staging 安装新 map |
| 8 | `_restore_exceptions` | 按 manifest 还原 lift-out |
| 9 | `_reinstall_dependencies` | **CLI** `reinstall_runtime_dependencies_cli`（见 §6） |
| 10 | `_run_database_migrations` | 子进程 ``python -m core.infra.db.migrate apply``；日志 ``userspace/.ntq/update/logs/migrate-<UTC>.log``；摘要 ``cache/last_migration_result.json`` → ``ctx.database_migration``。无快照默认 **失败**；``NTQ_UPDATE_ALLOW_MISSING_SCHEMA_SNAPSHOT=1`` 可跳过；``NTQ_UPDATE_SKIP_DB_MIGRATION=1`` 跳过整步 |
| 11 | `_trigger_core_extra_actions` | 子进程 ``python -m core.infra.update.post_upgrade run``；新版 ``core/infra/update/post_upgrade`` 注册表 **为空则跳过**；日志 ``logs/post-upgrade-<UTC>.log`` → ``ctx.post_upgrade``；``NTQ_UPDATE_SKIP_POST_UPGRADE=1`` 可跳过整步 |
| 12 | `_cleanup_staging` | ``helper.cleanup_after_upgrade``：删 ``staging/``、``inbox`` zip、已还原的 ``lift-out/``、``pre_mirror`` 快照；**保留** ``logs/`` 与 ``last_*_result.json``；``NTQ_UPDATE_SKIP_CLEANUP=1`` 可跳过 |

**禁止**：在 zip 内执行未校验脚本承担 schema 迁移；迁移与 DDL 在 **`core/infra/db`**（及受信任的子进程）内完成。

---

## 8.1 与 `core/infra/db` 的分工（数据库升级）

- **Diff / execution plan / DDL / 索引扒光策略 / 数据回填脚本查找** 均在 **`core/infra/db`**（及后续子模块）实现；约定见 **`core/infra/db/README.md`** 中「Schema 与升级」一节。  
- **Updater** 只负责：步骤 6 快照；步骤 10 **子进程** 调 ``core.infra.db.migrate``（日志落盘、结果回填 ``ctx.database_migration``）；不实现 SQL。环境变量见 §8 步骤 10。  
- **「旧版期望 schema」来源**：镜像后勿再从已被替换的 `core/tables` 反推旧版；应以该 JSON 快照（或等价内存结果）为升级前代码真源，与 **staging / 镜像后 `core/tables`**（新版期望）及 **当前库** 做 diff。  
- **表级稳定键**：`core/tables` 下各 `schema.py` 已要求 **`update_key`**（作者维护），用于迁移脚本与 diff 的 `action_id` 锚定；`userspace` 自定义表不要求。

---

## 9. 人机分工：要不要「记录跨版本变化」？

| 层面 | 是否需要 |
|------|-----------|
| **升级器算法** | **不需要**完整「从 V1 到 Vn 的变更链表」；每版自带 **当前 `managed_scope` + 完整 payload** 即可闭环。 |
| **CHANGELOG / Release** | **需要**，便于用户阅读破坏性变更、排障。 |
| **数据库** | **需要**单调 **revision** 链（迁移历史），与文件层分开。 |

---

## 10. 可选参考文件

| 文件 | 说明 |
|------|------|
| **`update_plan.example.json`** | **`managed_scope_mirror`** 草案（`plan_schema_version: 2`）。 |
| **`update_plan.delta.example.json`** | 旧草案（按条 `replace/create/remove`）；**不推荐**做主路径，跨版本易漏项，仅作对照。 |
| **`manifest.example.json`** | 将来 CDN / 多镜像 / 强制哈希时可启用。 |

---

## 11. 安全与诚实

- 传输尽量 HTTPS；后续可加 zip **sha256** 与 manifest 对齐。  
- UI 文案不误导读研结论。

---

## 12. 代码入口（骨架）

### 为何必须在 ``userspace/updater/``，而不是 ``core/`` 或 ``setup/``？

应用升级会替换 ``managed_scope`` 下的 ``core/``、也可能替换 ``setup/``；若在**正在执行的那份代码路径**里跑镜像，会遇到 **文件占用 / 无法覆盖**（尤其 Windows）。因此：

- **写盘升级**的编排脚本放在 **`userspace/updater/`**，通常不在发行 zip 的替换集合里；随 **init userspace** zip 解压后即可长期使用。
- **版本探测**（只 GET 远端 ``system.json``）仍可由旧版 **launcher / BFF** 调用（可与 ``pipeline.check_remote_has_newer_version`` 同逻辑；实现占位）。

### 仓库里的源文件在哪？

| 路径 | 说明 |
|------|------|
| **`setup/updater/pipeline.py`** | 与运行时 **`userspace/updater/pipeline.py`** 同源；打 **init userspace zip** 时把该目录运行时文件放进包内 ``updater/``，解压后落到 **`userspace/updater/`**。 |
| **`setup/updater/run_apply.py`** | CLI 入口占位；本地可 ``python setup/updater/run_apply.py`` 调试。 |

---

## 13. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-05-12 | 初稿至 FAQ、delta plan 等 |
| 2026-05-12 | **定稿**：`managed_scope` + zip 递归镜像、map 外不动、lift-out、删依赖重装、收尾顺序（依赖→DB）、与跨版本关系 |
| 2026-05-12 | 骨架固定在 ``setup/updater/`` → 随 init zip 进 ``userspace/updater/``（避免 ``core/``、``setup/`` 被替换时执行其中代码） |
| 2026-05-15 | 对齐已实现步骤：顶层 ``managed_scope`` 镜像、lift-out、CLI 依赖重装接口；补充与 ``core/infra/db`` 迁移分工及 §8 流水线表 |
| 2026-05-12 | §8：在 ``_update_managed_scope`` 前增加 ``core/tables`` schema 快照，保证迁移 diff 能拿到升级前代码期望 |
| 2026-05-15 | §8 步骤 10：DB 迁移子进程日志、结果 JSON、无快照默认失败策略 |
