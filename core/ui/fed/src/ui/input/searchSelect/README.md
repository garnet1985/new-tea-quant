# searchSelect

可搜索下拉：点击触发器展开，**面板顶部有搜索框**，过滤长列表后再点选。

```js
import SearchSelect from 'ui/input/searchSelect';

<SearchSelect
  label="策略"
  value={v}
  onChange={(e) => setV(e.target.value)}
  options={[
    { value: 'mom', label: '动量增强' },
    { value: 'mean', label: '均值回归' },
  ]}
  placeholder="搜索策略…"
  emptyLabel="请选择策略"
/>
```

与普通 `Select` 的区别：展开后有独立搜索输入，适合 options 很多的场景。菜单不模糊整页背景。
