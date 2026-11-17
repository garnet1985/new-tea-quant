# becomeMemberLink

> 状态：**已实现** · 路径 `ntq-ui/becomeMemberLink`

「成为会员」注册入口。**不发请求**；`href` 由 container / 页面传入。

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `href` | `string` | `''` | 注册页 URL；空则不渲染 |
| `label` | `string` | `'成为会员'` | 文案 |
| `variant` | `'button' \| 'link'` | `'button'` | 按钮样式或行内文字链 |

## 用法

```js
import BecomeMemberLink from 'ntq-ui/becomeMemberLink';

<BecomeMemberLink href={registerUrl} />
<BecomeMemberLink href={registerUrl} variant="link" />
```

`button` 走 `NtqButton`（外链自动后置 `>`）；`link` 为 `.ntq-link` + `chevronRight`。
