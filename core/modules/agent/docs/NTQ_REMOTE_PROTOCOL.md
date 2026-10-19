# NTQ Provider ↔ Website 状态协议

**版本：** `0.1.0-draft`  
**前提：** [PROVIDER_AND_NAVIGATOR.md](./PROVIDER_AND_NAVIGATOR.md)

本地 App 只打 **一个出入口**（OpenAI 兼容 `chat/completions` → `{ai_base}/chat/completions`）。  
Website 负责选模型与扣费；因此 **每次请求必须声明当前 Agent 状态**，不能靠猜 messages。

---

## 协议主体（定稿）

本协议只回答一件事：**这一次补全，App 处在链路的哪一步**，以便 Website 选模型、计价。

核心只有两层标记：

1. **`phase`（阶段）** — `navigate` | `act`  
2. **`intent`（act 种类）** — 仅当 `phase=act` 时必填，标明当前流向  

### 链路定义

**每一个用户 prompt** 对应一条完整执行链路，形状固定为：

```text
1 × navigate  →  0…N × act
```

| 步骤 | phase | intent | 含义 |
|------|--------|--------|------|
| 第 1 次模型补全（若需要分流） | `navigate` | `null` | 用户这句话进来，先 Navigator 出意图清单 |
| 随后 0…N 次模型补全 | `act` | 具体流向 kind | 按清单执行讲解 / 干活等 |

约定：

- **总是以 navigate 开头**（对该用户 prompt 而言）；不会先 act 再 nav。  
- **act 可以是 0 次**（例如本地固定文案：identity / advice 模板 / out_of_scope）。  
- **下一条用户输入 = 新开一条链路**，再来一遍 `1 × navigate → 0…N × act`；不把上一轮的 act 接到新 prompt 上当开头。  
- 同一次用户 prompt 里，navigate **最多一次**；之后只有 act（可多次，如 worker 工具循环）。

```text
用户 prompt #1
  └─ navigate
  └─ act (intent=guide)        ← 0…N
  └─ …

用户 prompt #2
  └─ navigate                  ← 新链路，重新 nav
  └─ act (intent=worker)
  └─ act (intent=worker)
  └─ …
```

---

## `phase` 与 `act` 定义

### `phase=navigate`

- **是什么：** 分流 / Navigator。根据用户原话（及必要 context）产出有序意图清单。  
- **何时：** 每个用户 prompt 的**第一条**模型请求（需要分类时）。  
- **`intent`：** 必须为 `null`（尚未选定流向）。  
- **Website：** 按「分流」档选模型（示例：deepseek-flash）。

### `phase=act`

- **是什么：** 执行阶段。Navigator 已给出出口，Agent 在某一流向上调用模型。  
- **何时：** 同链路内 navigate 之后的每一次模型补全。  
- **`intent`：** 必填，见下表（act 种类标记）。  
- **Website：** 按 `intent` 选模型与计价。

### `intent`（act 种类标记）

与本地 Navigator 出口对齐；未知值 Website 应安全降级（如按 `guide`）。

| intent | 含义 | 调度示例 |
|--------|------|----------|
| `guide` | 说明书 / wiki 循环 | glm-4-flash |
| `guide_arch` | 架构讲解 | glm-4-flash |
| `worker` | 写策略 / 回测等工具循环 | deepseek-flash |
| `identity` / `advice` / `out_of_scope` | 通常**本地固定文案、不打模型**；若打了则按 guide 档 | glm-4-flash |

---

## 为什么需要协议

| 本地阶段 | Website 通常该选 | 仅靠 `ntq_mode=ask\|work` 的问题 |
|----------|------------------|----------------------------------|
| navigate | 强分类模型 | 与「讲解」混在 ask 里 |
| act + guide* | 便宜问答 | 无法与 navigate 区分 |
| act + worker | 更强编码/工具 | 只有 work，没有显式阶段 |

---

## 请求形状（App → Website）

在 OpenAI body 上增加命名空间 **`ntq`**（Website 识别后剥离，勿原样转给上游模型供应商）：

```json
{
  "model": "auto",
  "messages": [/* App 组好的 context */],
  "max_tokens": 512,
  "temperature": 0.0,
  "ntq": {
    "phase": "navigate",
    "intent": null,
    "session_id": "default",
    "client": "ntq-app",
    "client_version": "0.1.0"
  }
}
```

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `ntq.phase` | string | 是 | `navigate` \| `act` |
| `ntq.intent` | string \| null | `act` 时必填；`navigate` 时为 `null` | act 种类 |
| `ntq.session_id` | string | 建议 | 本机会话名 |
| `ntq.client` | string | 建议 | 如 `ntq-app` |
| `ntq.client_version` | string | 建议 | App 版本 |

### App 发送规则

```text
每个用户 prompt（Provider = ntq）：
  1) navigate → complete(ntq.phase=navigate, intent=null)
  2) 若进入模型流向：
       guide / guide_arch → complete(phase=act, intent=…)  × 0…N
       worker             → complete(phase=act, intent=worker) × 0…N
  3) 本地固定回复 → 不请求 Website（该链路 act 次数为 0）
```

- 自备 Provider：**不传 `ntq` 块**。  
- 链路计数以**用户 prompt** 为边界，不以工具步或 HTTP 连接为边界。

---

## Website 侧职责

1. 校验会员 token、解析 `ntq` 块。  
2. 按 `(phase, intent)` → 内部模型路由表（可配置；App 不感知模型名）。  
3. 按路由结果计量猫粮（navigate 与各类 act 可不同单价）。  
4. 把 `messages` 转给选定上游；**不要**把 `ntq` 原样转给上游。  
5. 响应保持 OpenAI 形；可选回传：

```json
{
  "choices": [...],
  "usage": {...},
  "ntq": {
    "model_used": "deepseek-flash",
    "phase": "navigate",
    "intent": null,
    "catfood_spent": 0.02,
    "balance": 12.3
  }
}
```

---

## 与旧字段 `ntq_mode=ask|work`

| 旧 | 新 | 说明 |
|----|----|------|
| `ask` | 不够用 | 曾混用「便宜档」与「非 worker」 |
| `work` | ≈ `phase=act` + `intent=worker` | 不含 navigate |

**Drupal 新实现以 `ntq.phase` / `ntq.intent` 为准。**  
过渡期：无 `ntq` 块时，`ntq_mode=work` → `act+worker`，其余 → `act+guide`；**勿**把旧 `ask` 当成 `navigate`。

---

## 最小路由表（Website 配置示例）

```text
navigate           → deepseek-flash
act + guide*       → glm-4-flash
act + worker       → deepseek-flash
unknown intent     → glm-4-flash
```

模型名、单价、fallback **只在 Drupal**，不进 App。

---

## 非目标

- App 不传具体模型名（调试开关除外，默认关）。  
- 协议不承载本机工具落盘；只承载「这次补全的 phase / intent」。  
- 会话记忆以 App 拼进 `messages` 为主；`session_id` 供远端审计/限流。
