# ASCII Diagram 规范（草案）

> 目标：在 `md2html` 中稳定、可预期地把 ASCII 图转成结构化的 HTML（`<div class="shape-*">` + `<pre class="shape-tree">`），并约束写法，避免“解析不出来”或解析出错。

## 0. 使用方式

- 所有 ASCII 图必须放在 Markdown 代码块中，例如：

  ```text
  ┌───────┐
  │ Box A │
  └───────┘
  ```

- 推荐使用 `text` / `plaintext` 作为语言标识：

  ```text
  ...ASCII 图...
  ```

- 不符合本规范的图会被当作普通代码块原样输出（`<pre><code>…</code></pre>`），不会尝试解析。

---

## 1. 形状（Shape）类型

解析器只识别三类形状：

- **Heading**：图内标题行（无边框的纯文本）
- **Box**：完整矩形框
- **Tree**：由 `│ ├─ └─ ▼` 等字符组成的结构线

解析后大致结构为：

```html
<div class="shape-diagram">
  <div class="shape-heading">Strategy 模块</div>

  <div class="shape-box">
    <div class="shape-line">Scanner</div>
    <div class="shape-line">- 扫描股票，发现机会</div>
    <div class="shape-line">- 汇总统计</div>
  </div>

  <pre class="shape-tree">
│
├─▶ ConnectionManager
│   └── DatabaseAdapter
  </pre>
</div>
```

> 样式由主题中的 SCSS 定义；解析器只负责生成统一的 `shape-*` class。

---

## 2. Box 语法

### 2.1 基本规则（必须满足）

一个合法的 box 形如：

```text
┌─────────────────────┐
│  内容行 1           │
│  内容行 2           │
└─────────────────────┘
```

必须满足：

1. **顶边**：一行，包含一个 `┌` 和一个 `┐`，中间全部是 `─` 或空格。
2. **底边**：一行，包含一个 `└` 和一个 `┘`，并且这两个字符的列号**分别与顶边的 `┌` / `┐` 对齐**。
3. 顶/底之间的每一行：
   - 在 `left_col` 位置必须是 `│`；
   - 在 `right_col` 位置必须是 `│`；
   - 中间可以是任意文本（中文、空格、其它符号）。
4. 不允许半截边框：中间行不得出现 `┌ ┐ └ ┘ ┬ ┴ ├ ┤` 等角或连接符号。

解析后会变成：

```html
<div class="shape-box">
  <div class="shape-line">内容行 1</div>
  <div class="shape-line">内容行 2</div>
</div>
```

### 2.2 不允许的写法（会被当作普通 pre）

为了让解析器简单而稳定，**禁止**以下写法：

#### 2.2.1 共享边界的“表格”框

```text
┌─────┬─────┐
│ A   │ B   │
└─────┴─────┘
```

解析器无法可靠知道左边框属于哪个 box，**不要使用**。  
请改写为两个上下堆叠的 box：

```text
┌─────┐
│ A   │
└─────┘

┌─────┐
│ B   │
└─────┘
```

#### 2.2.2 在 box 内再画半截小框

```text
┌────────────┐
│ A ┌────┐   │
│   └────┘   │
└────────────┘
```

内部的小框不被支持，会破坏外框的识别。  
请改成纯文字或单独画一个 box。

> 简单记忆：**每个 box 的四条边只属于它自己，不给其它 box 用。**

---

## 3. 嵌套 Box

当前 **只支持「一层嵌套」**：  
- 顶层可以有多个大 box（outer）；  
- 每个大 box 内可以有多个小 box（inner）；  
- 小 box 里面**不能再嵌 box**。

示例：

```text
┌──────────────────────────────┐
│ Strategy 模块                 │
│                              │
│  ┌────────────────────────┐  │
│  │ Scanner                │  │
│  │ - 扫描股票，发现机会    │  │
│  │ - 汇总统计             │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

约束：

1. 子 box 的顶/底行必须完全在父 box 的内容区域内：  
   `parent.start_line < child.start_line < child.end_line < parent.end_line`。
2. 子 box 的 `left_col` / `right_col` 必须满足：  
   `parent.left_col < child.left_col` 且 `child.right_col < parent.right_col`。
3. 子 box 与父 box、不同行子 box 之间不能共用边界（同 2.2 的规则）。
4. 只使用**一层嵌套**（外框 + 若干子框）。更深层的嵌套会被视为不受支持的写法，解析器可能退回原始 `<pre><code>`。

解析后结构类似：

```html
<div class="shape-diagram">
  <div class="shape-box shape-box--outer">
    <div class="shape-line">Strategy 模块</div>

    <div class="shape-box shape-box--inner">
      <div class="shape-line">Scanner</div>
      <div class="shape-line">- 扫描股票，发现机会</div>
      <div class="shape-line">- 汇总统计</div>
    </div>
  </div>
</div>
```

---

## 4. 多个平级 Box

一个代码块中可以包含多个**平级** box（不嵌套），例如：

```text
┌──────┐
│ Box A│
└──────┘

┌──────┐
│ Box B│
└──────┘
```

解析后会变成：

```html
<div class="shape-diagram">
  <div class="shape-box">…Box A 内容…</div>
  <div class="shape-box">…Box B 内容…</div>
</div>
```

如何排列（上下堆叠 / 左右排列）由 CSS 控制，例如：

```scss
.shape-diagram > .shape-box {
  margin-block: 0.5rem;
}
```

> 注意：如果多个 box 之间存在箭头/竖线连接关系（如复杂流程图），首版解析可能只保留 box 自身，不保证还原所有连线。

---

## 5. Heading 规则

在一个 ASCII 代码块内，如果一行满足：

- 不包含任何 box/树状符号：`┌ ┐ └ ┘ │ ─ ┬ ┴ ├ ┤ ▼` 等；
- 去掉左右空格后是非空文本（中文 / 英文 / 标点）；
- 上下被空行或 box / tree 分隔；

则会被识别为一个 `heading`，输出为：

```html
<div class="shape-heading">Strategy 模块</div>
```

具体渲染为 `<div>` 还是 `<h4>` 由实现和 CSS 决定。

建议在 ASCII 图中使用类似：

```text
Strategy 模块

┌───────┐
...
└───────┘
```

---

## 6. Tree 规则

Tree 用于表达类似目录树或流程箭头，例如：

```text
│
├─▶ ConnectionManager
│   └── DatabaseAdapter
│       ├── PostgreSQLAdapter
│       └── SQLiteAdapter
```

规则：

- 所有**不在任何 box 内部**，且包含 `│` / `├` / `└` / `▼` 等符号的行，会被整体视为一个 tree 段；
- 当前版本不对 tree 做细粒度拆分，直接包成一个 `<pre class="shape-tree">…</pre>` 保留原始文本；
- 样式在 CSS 中通过 `.shape-tree` 控制，例如行高、左边距、颜色等。

---

## 7. Arrow 规则（Box 之间的箭头）

> 箭头用于表达「一个 box 的输出，流向另一个 box」。  
> 目前实现重点支持 **竖直向下的箭头**，并在同一父容器内建立结构化关系。

### 7.1 写法约定（竖直箭头）

在**同一个父容器**内（可以是顶层 diagram，也可以是某个大 box 内），多个 box 之间用一行只包含 `▼` 的箭头连接，例如：

```text
┌─────────────────────────────────────────────────────────────┐
│                    Strategy 模块                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Scanner                                 │  │
│  │  - 扫描股票，发现机会                                   │  │
│  │  - 汇总统计                                           │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                      │
│                     ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          AdapterDispatcher                           │  │
│  │  - 调用 Core Adapter                                 │  │
│  │  - 加载用户 Action                                   │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                      │
└─────────────────────┬──────────────────────────────────────┘
```

约束：

1. **父级范围**：箭头行必须在某个父容器的内部：  
   箭头所在行在 `parent.top < row < parent.bottom` 范围内。  
   - 父容器可以是**最外层 diagram**（大 box 之间的箭头）；  
   - 也可以是**某个大 box**（大 box 内的小 box 之间的箭头）。
2. **箭头行内容**：去掉外框边界和左右空格后，应只剩下一个 `▼`：  
   例如 `│         ▼        │`。
3. **起点/终点都在同一父容器内**：  
   箭头的列（`▼` 所在位置）必须**同时落在上下两个 box 的水平范围内**：
   - 向上找到最近的 box `from_box`，满足 `from_box.bottom < row` 且 `from_box.left < col < from_box.right`；
   - 向下找到最近的 box `to_box`，满足 `to_box.top > row` 且 `to_box.left < col < to_box.right`；
   - 二者的父级必须相同，即 `from_box.parent === to_box.parent`。
4. **不穿越内容，只能穿越空 border**：  
   在 `from_box.bottom` 和 `to_box.top` 之间，箭头所在列只能穿过：
   - 边框字符（`│ ┬ ┼ ┴ └ ┘` 等）；
   - 空格 / 空行。  
   一旦这一列在中途进入了某个 box 的**内容区域**（也就是有正文文本），该箭头会被视为**不合法通路**，不会被结构化连线。
5. **`┬` / `┼` 辅助标记（可选，但建议遵守）**：
   - 在某个 box 的底边，如果你希望箭头「从这里发射」，可以在箭头列画 `┬`；  
   - 如果你希望箭头「只穿过这个 box 的边框」，而不把它作为起点，可以在箭头列画 `┼`；  
   - 解析器在计算 `from_box` 时，会优先选择底边该列为 `┬` 的 box，底边为 `┼` 的 box 只作为“通路”，不当作起点。
6. 任何不满足上述条件的箭头行，会被当作普通文本 `▼` 处理（或者被忽略），**不会强行连线**。

> 目前**仅实现竖直 `▼` 箭头**的结构化解析；  
> 水平箭头（从左到右）可以用 ASCII 自由绘制，但暂不保证被转换为结构化连线。

### 7.2 渲染结果（竖直箭头）

解析成功时，箭头会被渲染成一个单独的 `shape-arrow` 元素，插在两个 box 之间，例如：

```html
<div class="shape-box shape-box--outer">
  <div class="shape-box shape-box--inner">
    <!-- Scanner 内容 -->
  </div>

  <div class="shape-arrow shape-arrow--down">▼</div>

  <div class="shape-box shape-box--inner">
    <!-- AdapterDispatcher 内容 -->
  </div>
</div>
```

样式和连线细节由 CSS / JS 决定。解析器只负责提供「谁指向谁」的结构顺序。

> 分叉（一个 box 指向多个 box）可以通过**多条箭头行**表达：  
> 对每个目标 box 分别写一行 `▼`，解析器会得到多条 from→to 关系；  
> 更复杂的 ASCII 分叉（如 `┬` 树形）仍建议保留在 `shape-tree` 中展示。

---

## 8. 解析失败的情况（保持原样）

解析器遇到以下情况时，会**放弃解析**，直接输出原始 ASCII 图：

1. 任意 box 违反了 2.1 的基本规则（边不对齐、缺角、边上有奇怪字符等）。
2. 存在共享边界或半截框（见 2.2）。
3. 嵌套不满足「完整包含」关系（子 box 边界贴在父 box 边框上或跨出父框）。
4. 出现多层复杂嵌套且不符合本规范（例如 box 里再嵌 box，再嵌 box）。
5. 解析过程中形成的 box 树结构不一致或含有交叉重叠。

一旦放弃解析，该代码块会变成普通：

```html
<pre><code>…原始 ASCII 文本…</code></pre>
```

---

## 9. 建议的写法小结

为了让解析更稳、样式更统一，推荐遵守以下习惯：

1. **一个图一类目的**：比如「整体架构图」一张图里只画主流程；细节拆到别的图或文字表述。
2. **优先使用单层 box 或“一层嵌套”**：外框 + 几个子框，复杂流程另起一张图 / tree。
3. **避免“表格式 box”**：不要用 `┌─┬─┐` 这类拼多列格子，改成多个 box 上下放即可。
4. **多 box + 箭头**：
   - 强烈建议优先使用「同一父容器内的、竖直向下箭头」：  
     - 大 box ↔ 大 box（顶层兄弟之间）；  
     - 同一大 box 内的小 box ↔ 小 box；  
   - 箭头只在一条**干净的竖直列**上向下穿越，列中间不要夹杂正文内容。
5. **遇到不确定写法时宁可简单**：能用文字 + 单一 box 说明清楚的，就不要硬画复杂 ASCII，尤其是跨多层嵌套的箭头。

后续如果需要支持更多模式（例如一行多个小 box、自动识别箭头连线等），可以在本规范基础上另行扩展。

