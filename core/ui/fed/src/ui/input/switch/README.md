# switch

开关（标签左、开关右）。`onChange` → `e.target.checked`。

```js
import Switch from 'ui/input/switch';

<Switch label="启用" checked={on} onChange={(e) => setOn(e.target.checked)} tip="说明" />
```
