# select

基础下拉。

```js
import Select from 'ui/input/select';

<Select
  label="周期"
  value={v}
  onChange={(e) => setV(e.target.value)}
  options={[
    { value: 'd', label: '日' },
    { value: 'w', label: '周' },
  ]}
/>
```

需搜索过滤时用 `searchSelect`。
