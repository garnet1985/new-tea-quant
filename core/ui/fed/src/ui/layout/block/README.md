# block

> 路径 `ui/layout/block`

块级容器。表面（背景 / 玻璃 / 渐变）与圆角用语义 token；数值只在全局 CSS。

```js
// ✅
<Block padding="md" gap="sm" surface="soft" radius="md" />
<Block surface="glass" radius="lg" bordered padding="md" />
<Block surface="panel" radius="none" padding="md" /> // 侧栏式无圆角
<Block surface="soft" radius="pill" padding="sm" />  // 胶囊

// ❌
<Block padding={16} style={{ borderRadius: 8 }} />
```

## 参数摘要

| 参数 | 取值 | 默认 |
|------|------|------|
| `padding` / `gap` | `none`…`xl` | `md` / `none` |
| `radius` | `none` `sm` `md` `lg` `pill` | 未传时：`bordered`→`md`，否则 `none` |
| `surface` | `none` `soft` `panel` `glass` `gradient` | `none` |
| `bordered` | boolean | `false` |

改数值：覆盖 `--ntq-space-*` / `--ntq-radius-*` / `--ntq-surface-*` / `--ntq-blur-*`。
