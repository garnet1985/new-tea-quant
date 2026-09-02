# Settings 身份与 Effective：讨论纪要

日期：2026-09-02  
结论（已拍板）→ [DECISIONS.md](./DECISIONS.md)  
布局与旧批次 → [VERSIONING_REDESIGN.md](./VERSIONING_REDESIGN.md)

本文保留推理、否决项和仍开放的点，避免把讨论细节塞进 decision 表。

---

## 1. 起因

工作台出现三类症状，根子是 **version / effective / 编辑器草稿** 不是同一套投影：

- 重跑枚举后胶囊误报「设置已变更」
- 跑价格回测时 version 从 v4 跳到 v1，切步又跳回来
- 三步都跑完后，步骤间跳转，已完成步骤在步进器上变回未跑

前端竞态（快照同步吃整份 `executionState`、切步丢掉 `location.state` 重拉 latest、`force_refresh` 一律新 vid）是表层。真正要定的是身份模型。

---

## 2. 两轴不要绑在一起

曾有一种意见：把 settings 拆成物理 blocks，就能「天然」得到分步缓存。那是把两件独立的事绑在一起了：

| | 一次哈希（整次回测） | 每步自己哈希 |
|---|---|---|
| 单文件 + 功能块白名单 | 现在的方向 | 每步声明依赖哪些块 |
| 多 block 文件 | 把所有 effective 块一起哈希 | 每步声明依赖哪些文件 |

分步缓存来自 **指纹粒度**，不是来自磁盘切了几个文件。单文件也可以按步哈希；多文件若仍对全部 effective 块打一次哈希，不会多出任何缓存命中。

块内部仍会有空 `{}`、UI 草稿、`1` vs `1.0`。非 effective 块不进指纹，和今天把 `meta` / `enumerator` 排除是同一件事。canonicalize 在两种存储下都要做。

---

## 3. 配置粒度 vs 业务拆法

**问题 1（次要）：** 一个大 `settings.py` 还是多个小文件。  
都行。多个文件 UX 可能稍好（只打开要改的块）。不得按步骤做成三份文件。

**问题 2（关键）：** 按步骤拆还是按功能拆。这决定指纹是「一步」还是「一次完整回测」。

按步骤拆（每步一组 settings，即便由程序抽取）：

- 共用项（`core`、区间、市场规则）会复制或必须再做共享层
- 价格/投资的身份必须含上游产物，不能只哈希「本步那一组」
- 用户可见 version 会变成树：一次操作可能挂多个号，恢复/对比不知道对齐哪一层

按功能拆（`core` / `goal` / `simulation` / `portfolio` …，多步共用）：

- 与用户理解的策略语义一致
- 步骤用引擎里的依赖清单引用块（程序拆分：用户不养三份配置）
- 指纹仍可选择「全部 effective 块一次哈希」——与「一个回测一个 version」一致

**拍板：** 功能块 + 一次回测一个 version。分步缓存能省上游重算，但用户面对的 version 会变成 DAG，否决。

---

## 4. Effective 怎么来

一次回测一份 effective。它是完整 settings 的 **白名单投影**，不是另一种互相加密的格式。

- `settings → effective`：抽出功能块，canonicalize。丢掉「其他」字段（展示名、enumerator 调度、analysis…）。
- `effective → settings`：merge 回完整文件，其他字段保留。恢复走这条，不是从 effective 单独还原整个 `settings.py`。

因此两边不能无损互转。归档以 **当时完整 settings** 为准；effective 可再存一份便于展示/校验。core 变了，旧 effective 只作历史，不能拿新算法重算去命中缓存。

「主动改设置」不靠点击追踪。被动改（切步填默认、migrate、pprint、类型抖动、空对象）只要两边都先投影到同一套 canonical effective，哈希就一样。能改变回测结果的进白名单；进了白名单的 UI 草稿 key 要从投影剔除。

---

## 5. 同 env 下切到某 version

目标：env 没变、effective 一致时，用户切到 version N，应能 **继续补跑或复写任一步，号仍是 N**。

现在做不到，是因为已完成步骤走 `force_refresh` / `ignore_cache`，D10 被理解成「凡 force 必新号」。

正确对照：

- 同 env + 同 effective + 补步或复写 → 写 N（复写上游则删下游产物）
- effective 变了 → 新号
- 只改非 effective → 不换号

「切换到 N」要能继续跑，前提是工作集的 canonical effective 就是 N 的 freeze。编辑器仍是后来改过的 settings 时，点运行应对不上 N（胶囊「设置已变更」），而应新开号。切版本后是否强制弹出「恢复配置」，见文末开放项。

---

## 6. `env_fp` 变了怎么办

曾考虑原地覆盖旧 `{vid}/`，让用户看不到「引擎升级导致结果变了」。否决：用户记得的是数字。同一号里报告自己变了，更像引擎不稳。存储布局一变，原地覆盖还要写旧格式，兼容成本高于新开号。

正确模型：

- 旧 version 变 **档案**：可看、可对比、可恢复配置；不可 hit、不可补步、不可写入
- 在旧 version 上点运行 = 用这份 effective 在 **当前 env** 下找 `(settings_fp, 当前 env_fp)`：命中已有新号，或新建
- 主列表按 settings 身份聚合，突出当前 env 那一个；旧 env 标「环境已失效 / 仅供查阅」
- 文案：「当前环境已更新」，不写「引擎算错了」
- 不因 env 变化批量删除；keep-N 时可优先淘汰未钉住的失效 version

registry 上可以打 `env_invalid`；`{vid}/` 里的产物不动。

---

## 7. 与 VERSIONING_REDESIGN D1–D14 的关系

仍有效：D1 D2 D3（被 D15 收紧）D4 D5 D6 D8 D9（被 D27 收紧）D11（被 D17 扩展到复写）D12 D13 D14。

修订：

- **D7**：不只冻 effective 子集，必须冻完整 settings
- **D10**：仅「当前 env 下还没有同一 settings_fp」时新开号；不是凡 force 必新号。同 env 复写走 D17

---

## 8. 开放项（2026-09-02 已拍板，见 DECISIONS）

1. 复写上游 → **删下游**（D18）。
2. 恢复改 `settings.py`；**运行与选中 version 解耦**（D32–D33）。失效目录只读，Run 不因「正在看旧号」报错。
3. 两种 fp：可逆执行输入 → `execute_fp`（settings + scope），不可逆 → `env_fp`。现实现把区间混进 `env_fp`、把 `entity_ids` 双边哈希，要按 D34–D36 拆开。
4. 先单文件；按功能拆多文件以后再做（D21）。
5. keep-N：未 pin、号更靠前的先删；即将过期是后期 UI（D31）。
6. 当前 env 尚无结果：胶囊可挂旧号 +「环境已更新 / 当前环境尚无结果」，主按钮重跑到新号（D37）。
