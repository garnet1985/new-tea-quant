# block

> 路径 `ui/layout/block`

块级容器。表面（背景 / 玻璃 / 渐变）与圆角用语义 token；数值只在全局 CSS。

```js
// ✅ 不传 gap → 默认 1rem
<Block surface="soft" radius="md" bordered />
<Block surface="glass" radius="lg" bordered />
<Block surface="panel" radius="none" gap="none" /> // 紧凑再显式 none
<Block surface="soft" radius="pill" padding="sm" />

// ❌
<Block padding={16} style={{ borderRadius: 8 }} />
```

## 参数摘要

| 参数 | 取值 | 默认 |
|------|------|------|
| `padding` / `gap` | `none`…`xl` | 均为 `md`（gap = 1rem） |
| `radius` | `none` `sm` `md` `lg` `pill` | 未传时：`bordered`→`md`，否则 `none` |
| `surface` | `none` `soft` `panel` `glass` `gradient` | `none` |
| `bordered` | boolean | `false` |

改数值：覆盖 `--ntq-space-*` / `--ntq-radius-*` / `--ntq-surface-*` / `--ntq-blur-*`。
