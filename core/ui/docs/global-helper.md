# Global Helper（全页引导）

**版本：** `0.1.0`  
**状态：** 文档、存储、UI 引擎已落地；第一份 help 为制定策略内页三栏

全页黑遮罩 + 挖洞高亮，按「一类路由一份 help」引导用户（尤其是首次）认识页面上的控件。不是字段旁的 `NtqHelpTooltip`，也不是 AI 百科。

---

## 1. 概念

| 词 | 含义 |
|----|------|
| **help** | 一份引导。对应一类路由，不是某一个 URL。 |
| **helpId** | 该份引导的稳定产品 ID，例如 `strategy-design`。与路径字符串无关。 |
| **step** | 一次换高亮目标（换一个 DOM）。 |
| **page** | 同一个高亮里的一页讲解（翻页，不换洞）。 |
| **target** | step 要挖洞的锚点：`[data-ntq-help="<id>"]`。 |
| **关闭** | 用户点「我知道了」或「跳过」：只关这一份 `helpId`，并写入 userspace。 |

三层：`help → steps[] → pages[]`。

---

## 2. 两份数据，互不混放

| | 放哪 | 谁改 | 内容 |
|--|------|------|------|
| **目录（catalog）** | FED 代码 | 发版 | `helpId`、路由匹配、`version`、steps、文案、图片、target |
| **关闭账本** | `userspace/system/config/ui_helper.json` | 用户点关闭 | 哪些 `helpId` 在哪个 `version` 上被关过 |

userspace **不存** 路由、文案、DOM 选择器。JSON 过时指的是账本里的 id/version，不是目录本身。

路由变了，改 FED 的 `match`。新复杂页要引导，在目录里加一条新 `helpId`。账本不用预知未来页面。

---

## 3. 何时出现

- 当前 pathname **匹配到** 某条 catalog help → 显示 help 按钮；若该 help **未关闭** 则自动弹。
- **匹配不到** → 按钮没有、不弹、什么都不做。landing / 策略列表等默认不配。
- 匹配按 **路由类**：路径变量、query 不拆份。`/strategy-design/foo/enum` 与 `/strategy-design/bar/price` 可以是同一 `helpId`。
- 自动弹必须等关闭账本 GET 回来，且页面不在整页 loading、没有更高优先级 overlay（setup 同意、welcome intro）。
- 高亮期间 **不能** 点被高亮的控件；遮罩吃掉交互。
- 「我知道了 / 跳过」只关 **当前这份** help，其它 help 不受影响。

制定策略按 **当时 DOM 是否还在** 切 help，不按「四步必须一份」：

| helpId（示例） | 匹配 | 原因 |
|----------------|------|------|
| `strategy-design` | `/strategy-design/:name/(enum\|price\|portfolio)` | 设置栏 / 执行区 / 报告区同一套壳 |
| `strategy-design-decision` | `/strategy-design/:name/decision` | 对局 DOM 与上表不同时存在；需要时再加 |

第一刀引擎只用占位 help 验证闭环，不写正式文案。

---

## 4. 路由变了、JSON 过时、新页面要 help

### 4.1 原则：`helpId` 是产品面，不是 URL

`helpId` 一旦发出去就尽量不改。路径从 `/strategy-design/:name/enum` 改成别的，只改 catalog 的 `match`。已经关闭的用户不会因为改路由再被弹一次。

### 4.2 四种演进

| 发生了什么 | 怎么做 | 已关闭的用户 |
|------------|--------|----------------|
| 同一类页改路径 / 改 query | 只改 `match`，`helpId` 不动 | 仍关闭 |
| 新复杂页需要引导 | 目录新增 `helpId` | 新 id 不在账本里 → **自动弹** |
| 某页不再需要引导 | 从目录删掉该 help | 按钮/自动都没了；账本里的旧 key **保留、读时忽略** |
| 一份 help 拆成两份 | 新 id 进目录；旧 id 可删或留作 `legacyIds` | 新 id 会弹；旧账本不算新 id 已关 |

禁止：把当前路由字符串写进 userspace。禁止：启动时按目录「重写/清空」整个账本（会丢掉仍有效的关闭记录）。

### 4.3 `version`：同一 `helpId` 的引导被改到必须再讲一遍

目录每条 help 有整数 `version`，缺省 `1`。关闭时把当时的 version 写入账本。

- 账本 version **≥** 目录 version → 视为已关闭（不自动弹；按钮仍可重开）。
- 账本 version **<** 目录 version → 视为未关闭，再自动弹一次。关闭后覆盖为新 version。
- **不要**为改错别字、换图而 bump。只有结构变了（新 step、目标换了、讲解与现界面不符）才 +1。

新页面走新 `helpId`，不要复用旧 id 再靠 bump 混充。

### 4.4 改名

尽量不改 `helpId`。若必须改，目录上写 `legacyIds`：账本里旧 id（且 version 有效）也算已关闭。写入只用新 id。

### 4.5 账本里的未知 key

BFF 不认识 catalog。多出来的 `helpId` 原样保存。FED 读到不在目录里的 key：忽略，不报错，不删除。以后若重新启用同 id，旧关闭记录仍然有效。

---

## 5. 找不到 DOM 怎么办

**找不到目标 ≠ 用户已看过。禁止因此写账本。**

每个 step 必须有 `target`。解析：`document.querySelector('[data-ntq-help="' + target + '"]')`，且元素有非空盒（宽高 > 0）。

### 5.1 解析时机

1. 先等页面离开整页 loading。
2. 当前 step 目标不在：短等（约 0.5–1s，raf / 轮询）。DOM 后挂上则继续。
3. 仍没有： **跳过该 step**，不挖空洞，不把内容卡悬在空白上。
4. 对剩余 step 重复；只用「此刻找得到」的 step。

### 5.2 整份 help 一个目标都没有

| 入口 | 行为 |
|------|------|
| 自动弹 | **这次不弹**。不写账本。下次进这类页再试。 |
| 点了 help 按钮 | **不打开遮罩**。不写账本。不报大错。 |

按钮是否渲染只看 **路由是否匹配 catalog**，不看 DOM 此刻在不在（避免 loading 时按钮闪没）。

### 5.3 进行到一半目标没了

遮罩已打开时当前目标卸载（例如切到 decision）：跳到下一件仍在的 step；后面都没有则 **收起遮罩且不写账本**。用户并未确认「我知道了」。

### 5.4 编写约束

step 只指向该路由类 **进页就稳定存在** 的节点。不要指折叠面板内部、跑完才出现的报告块、未打开的对话框。某 step 的 DOM 与另一 step 互斥（工作台 vs 对局），应拆成不同 `helpId`，而不是写进同一份再指望运行时跳过。

---

## 6. 关闭账本（下一阶段实现）

路径：`userspace/system/config/ui_helper.json`（经 `ProjectContext.path.get_user_config_root()`，禁止硬编码）。与 `feedback_prefs.json` 同类：升级保留 userspace，换浏览器仍有效。

```json
{
  "dismissed": {
    "strategy-design": {
      "version": 1,
      "at": "2026-09-18T07:00:00Z",
      "source": "ack"
    }
  }
}
```

- `source`：`ack`（我知道了 / 看完）或 `skip`（跳过）。两者都算关闭。
- `at`：UTC ISO8601。
- 文件不存在 = 谁都没关过。
- 损坏 / 非对象：当作空账本，不抛给 UI 崩溃。
- 写入用已有原子写（`bff/shared/file_ops.atomic_write_text`）。

归属：`platform/app_settings`（应用级 UI 偏好，不是 strategy 域）。

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/api/v1/settings/ui-helper` | 读账本 |
| POST | `/api/v1/settings/ui-helper` | 关闭一份 help |

GET `message`：

```json
{
  "dismissed": {
    "strategy-design": { "version": 1, "at": "2026-09-18T07:00:00Z", "source": "ack" }
  }
}
```

POST 请求：

```json
{ "helpId": "strategy-design", "version": 1, "source": "ack" }
```

- `helpId` 非空字符串；`version` 正整数；`source` 为 `ack` 或 `skip`。
- 幂等：同一 `helpId` 再 POST 则覆盖 `version` / `at` / `source`。
- 成功 `message` 与 GET 相同（整本账本）。
- BFF **不校验** `helpId` 是否仍在 FED 目录里。
- GET 失败：不自动弹；按钮在匹配到 help 时仍显示，手动打开不依赖账本。
- POST 失败：本会话内存视为已关（避免连点），下次进页若文件没写上会再自动弹。

字段 camelCase，信封遵循 `global-api-rules.md`。

---

## 7. 目录形状（FED，UI 阶段）

```js
{
  id: 'strategy-design',
  version: 1,
  legacyIds: [],
  match: (pathname) => boolean, // 一类路由
  steps: [
    {
      target: 'design-stepper',
      pages: [
        { title: '…', body: '…', image: '/help/optional.png' },
      ],
    },
  ],
}
```

- `id` 稳定、kebab-case、产品面命名，不是 path。
- 未匹配任何 help 的页面：host 存在但不渲染按钮/遮罩。
- 占位 help 只为打通自动弹、翻页、关闭、换浏览器不再弹；正式文案后补。

锚点：`data-ntq-help="design-stepper"`。不靠 CSS class 或可见文案。

---

## 8. UI 行为（再后一阶段）

- Host 挂在 `MainLayout`，与 `AssistantChatDock` 并列，不进 assistant 模块。
- Help 按钮：AI FAB 下方，同尺寸圆钮，无 glow / 无 aurora，图标 `help`。
- 遮罩 z-index：高于导航与 AI（1250），低于 setup 同意（1400）。
- 挖洞随 `getBoundingClientRect()`，resize / scroll 重算。
- 内容卡避开洞口。Esc 等同跳过当前 help（写账本 `source: skip`）。
- 进行中不要同时打开 AI 面板。

---

## 9. 实现顺序

1. **文档**（本文件）
2. **存储**：账本读写 + GET/POST + 单测（坏文件、幂等、未知 helpId）— 已做
3. **UI**：遮罩、挖洞、内容翻页、按钮 — 已做
4. **集成**：MainLayout + `strategy-design` 占位 help（设置 / 执行 / 报告）— 已做

未到的阶段不要提前给所有页面打锚点。

未到的阶段不要提前铺文案或给所有页面打锚点。
