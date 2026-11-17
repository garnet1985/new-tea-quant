# field

表单字段壳：标签布局 + tip / hint / error。

```js
import Field from 'ui/input/field';

<Field label="名称" tip="显示名" hint="可选">
  <input id="name" />
</Field>

<Field label="代码" labelPlacement="inline" error="必填">
  …
</Field>
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `label` | ReactNode | `''` |
| `labelPlacement` | `above` `inline` `none` | `above` |
| `tip` | ReactNode | — |
| `hint` / `error` | ReactNode | — |
| `required` | boolean | `false` |
