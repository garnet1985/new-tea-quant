# checkbox

复选框。

```js
import Checkbox from 'ui/input/checkbox';

<Checkbox label="启用该策略" checked={on} onChange={(e) => setOn(e.target.checked)} />
<Checkbox fieldLabel="协议" label="我已阅读" tip="打开全文" />
```

- `label`：勾选框右侧文案  
- `fieldLabel`：可选字段标签（配合 `labelPlacement`）
