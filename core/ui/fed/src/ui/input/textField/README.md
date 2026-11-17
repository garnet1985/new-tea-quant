# textField

单行文本输入。

```js
import TextField from 'ui/input/textField';

<TextField label="名称" value={v} onChange={(e) => setV(e.target.value)} />
<TextField label="代码" labelPlacement="inline" tip="唯一标识" />
<TextField labelPlacement="none" placeholder="无标签" aria-label="搜索词" />
```

常用：`label` `labelPlacement` `tip` `hint` `error` `value` `onChange` `type` `disabled` `placeholder` `required`。
