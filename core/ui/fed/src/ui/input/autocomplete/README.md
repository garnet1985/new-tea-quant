# autocomplete

可输入过滤 + 建议选择（可多选）。`onChange` 为 `e.target.value`。

**不要并进 TextField / SearchSelect**：

- vs TextField：带建议列表
- vs SearchSelect：输入框即过滤区，非「触发器 + 面板内搜索」

```js
import Autocomplete from 'ui/input/autocomplete';

<Autocomplete
  label="执行单元"
  options={[{ value: 'a', label: '单元 A' }]}
  value={v}
  onChange={(e) => setV(e.target.value)}
/>
```
