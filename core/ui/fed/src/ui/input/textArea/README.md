# textArea

多行文本输入。

```js
import TextArea from 'ui/input/textArea';

<TextArea label="备注" rows={4} value={v} onChange={(e) => setV(e.target.value)} />
```

`rows` 为最小行数（默认 4）。其余标签参数同 `TextField` / `Field`。
