# column

> 路径 `ui/layout/column`

分栏布局。用描述性 **`variant`** 选版式（纯 CSS class），不在 JS 里拼列数或像素。

## variant

| variant | 含义 |
|---------|------|
| `halves` | 两等分 |
| `thirds` | 三等分 |
| `quarters` | 四等分 |
| `asideMain` | 左窄右宽（约 1:2） |
| `mainAside` | 左宽右窄（约 2:1） |
| `sidebar` | 左固定侧栏 + 主栏 |
| `sidebarEnd` | 主栏 + 右固定侧栏 |

## 其它

| 参数 | 取值 | 说明 |
|------|------|------|
| `gap` | `none`…`xl` | 列间距 |
| `divider` | `none` `line` | 列间竖线（常与 `gap="none"` 搭配） |
| `align` | `stretch`… | align-items |
| `stack` | boolean | 窄屏是否单列 |

表面（背景 / 圆角 / 模糊）放在子级 **Block**，不要塞进 Column。

```js
// ✅
<Column variant="thirds" gap="md" />
<Column variant="sidebar" gap="none" divider="line">
  <Block surface="panel" radius="none" padding="md">侧栏</Block>
  <Block padding="md">主区</Block>
</Column>

// ❌
<Column kind="thirds" />
<Column columns={3} />
```
