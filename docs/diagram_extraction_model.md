# 框图抽取模型（Step 1 输出）

第一步的目标：从 ASCII/Unicode 框图文本中**正确抽取**结构化内容，供第二步用流程图库渲染。  
本文档约定「抽出来长什么样」以及 **align（对齐）** 的规则。

---

## 1. 输出结构（Content）

```json
{
  "nodes": [
    {
      "id": "n1",
      "label": "可选短标签，用于连线",
      "content": [
        { "text": "Strategy 模块", "align": "center", "indent": 20 },
        { "text": "- 扫描股票，发现机会", "align": "left", "indent": 2 },
        { "text": "- 汇总统计", "align": "left", "indent": 2 }
      ],
      "children": ["n2", "n3"]
    },
    { "id": "n2", "content": [ ... ] },
    { "id": "n3", "content": [ ... ] },
    { "id": "n7", "content": [ ... ], "children": ["n8", "n9", "n10"], "childrenLayout": "parallel", "parallelRows": [["n8", "n9", "n10"]] }
  ],
  "edges": [
    { "from": "n2", "to": "n3", "direction": "down" },
    { "from": "n6", "to": "n7", "direction": "down", "label": "用户实现" }
  ]
}
```

- **nodes**：每个 box 对应一个节点；`content` 为框内**有文字**的行（不含空行）。
- **content[].text**：该行清洗后的文案（去边框、去尾空白；列表行保留前导 `- ` 等）。
- **content[].align**：`"left"` | `"center"`；**content[].indent**：前导空格数。
- **空行**：不保留；框内空行在抽取时丢弃，渲染时用 padding/margin 控制间距。
- **node.childrenLayout**（可选）：当该节点有多个子 box 且至少有一行上有多个子 box 时，为 `"parallel"`。
- **node.parallelRows**（可选，与 childrenLayout 同现）：按行分组的子 box id，`[[row1_ids], [row2_ids], ...]`，每行内按 left 从左到右；一行一个 box 时该行仍单独成组。例如 3 个一排为 `[["n8","n9","n10"]]`，两排各 3 个为 `[["n1","n2","n3"], ["n4","n5","n6"]]`。
- **node.attachedContent**（可选）：紧贴在该 box **下方**、在下一子 box/箭头之前的文字行（如树形 ├─▶ StockService、├── ListService），格式同 `content`，表示「挂在该节点下的说明」。
- **edges**：箭头关系；**from / to** 为箭头前后实际 box 的 id；**label**（可选）为箭头上一行的文字（如「用户实现」「传递数据」），已去框线字符。

---

## 2. Align（对齐）规则（与 §4 一起定稿）

框内常见两种排版：

- **居中**：如 block 的 title（如「Strategy 模块」「Scanner」），在框内左右留白大致相等。
- **居左**：如列表项、说明文字，贴左或带固定缩进。

### 2.1 判定方式（基于「行内」宽度）

对**已经去掉左右边框**的一行 `inner`（只含框内内容）：

1. 取**内容区间**：`contentStart` = 第一个非空白字符下标，`contentEnd` = 最后一个非空白字符下标（若整行空白则视为空行，`align` 可定为 `left`）。
2. 行内宽度：`W = inner.length`（或去掉行尾 `│` 后的长度）。
3. 左空隙：`leftGap = contentStart`；右空隙：`rightGap = W - 1 - contentEnd`。
4. **居中**：当 `leftGap` 与 `rightGap` 的差值 ≤ 阈值（如 1～2 个字符），即视为居中，否则为**居左**。

公式化：

- 若 `|leftGap - rightGap| <= 2` → `align = "center"`；
- 否则 → `align = "left"`。

空行：`align = "left"`，`text = ""`。

### 2.2 示例（与文档一致）

| 行内容（inner） | leftGap | rightGap | align   |
|----------------|---------|----------|---------|
| `"                    Strategy 模块                            "` | 大     | 大且≈左  | center  |
| `"              Scanner                                 "`       | 大     | 大且≈左  | center  |
| `"  - 扫描股票，发现机会                                   "`    | 小     | 大       | left    |
| `"  - 汇总统计                                           "`      | 小     | 大       | left    |

这样第二步渲染时：对 `align === "center"` 的行用 `text-align: center`（或等价）；对 `align === "left"` 的行用 `text-align: left`，即可还原「标题居中、正文居左」的版式。

---

## 3. 与现有解析的关系

- 当前 `md2html.html` 里已有：框检测、父子关系、框内行清洗（去 `│`、trim、列表行识别）。  
- **抽取**时在**同一处**对每一行多做一步：在得到 `inner` 后按 2.1 算 `leftGap` / `rightGap`，得到 `align`，再填入 `content[]`。  
- 先保证「能正确抽出 content + align」，第二步再把这套结构交给 Mermaid/flowchart 等库或自渲染，即可。

---

## 4. 居左行的缩进与 tree 结构（讨论）

居左的行里，**bullet / 列表项常有缩进**（例如 `"  - 扫描股票"` 前有 2 个空格）。若抽取时把 leading space 去掉或统一 trim，会破坏层级感，甚至破坏 tree 结构。所以需要单独约定。

### 4.1 目标

- **居中**：仅用于「整行内容在框内视觉居中」的标题行，判定要稳，不要误把带缩进的列表当居中。
- **居左**：其余都算居左；**缩进要保留**，不能因为「居左」就把行首空格删掉。

### 4.2 识别居中 vs 居左（算法讨论）

沿用「行内左右空隙」思路，但写清楚边界：

- 对**未 trim 的**一行 `inner`（仅去掉行尾 `│` 即可）：
  - `contentStart` = 第一个非空白字符下标，`contentEnd` = 最后一个非空白字符下标。
  - `leftGap = contentStart`，`rightGap = W - 1 - contentEnd`（W = 行内宽度）。
- **居中**：`|leftGap - rightGap| <= 阈值`（例如 2）。  
  - 含义：内容在行内**左右留白近似相等**，典型是 title。
- **居左**：否则一律居左。  
  - 包括：有缩进的列表（`  - xxx`）、无缩进正文、空行等。

需要定的只有两件事：

1. **阈值**：2 是否合适？若框很宽、标题较短，左右差 3～4 个字符仍算居中可考虑阈值 3 或 4。
2. **空行**：整行空白时 `contentStart`/`contentEnd` 可定义为「无内容」；约定为 `align = "left"`、`text = ""` 即可。

这样不会把「前面有缩进的 bullet」判成居中（因为 leftGap 小、rightGap 大，差很大）。

### 4.3 缩进如何保留（不破坏 tree）

两种常见做法，二选一或兼容：

- **方案 A：在 `text` 里保留前导空格**  
  - 例如 `text: "  - 扫描股票，发现机会"`。  
  - 优点：和源一致，实现简单。  
  - 缺点：渲染时要自己把空格画出来（等宽字体下自然保留；若用 margin 则要先数空格再转成 indent）。

- **方案 B：单独字段表示缩进，`text` 为「去掉前导空格」的正文**  
  - 例如 `indent: 2, text: "- 扫描股票，发现机会"`。  
  - 优点：第二步用 `margin-left: indent * 0.5em` 或层级样式即可，不依赖空格宽度，tree 结构清晰。  
  - 缺点：需要约定单位（空格数 vs 层级 level）。

建议：**优先方案 B**（`indent` + 去前导空格的 `text`），便于流程图库和 tree 渲染；若希望与源完全一致，可同时保留「原始行」或带空格的 `textRaw` 供调试。

### 4.4 输出结构里如何体现（待定稿）

若采用方案 B，`content` 可写成：

```json
{ "text": "- 扫描股票，发现机会", "align": "left", "indent": 2 }
```

若采用方案 A，则不增加 `indent`，在 `text` 里保留前导空格。  
**当前文档先不写死，等方案定稿后再统一改 1 的示例和实现。**

---

## 5. 可选扩展

- **right**：若将来有右对齐需求，可增加 `rightGap << leftGap` 时 `align = "right"`。  
- **title / body 分离**：若第二步库需要「标题 + 正文」两段，可在后处理里把首段连续 `align === "center"` 的行合并为 `title`，其余为 `body`。
