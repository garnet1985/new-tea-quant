# radio（RadioGroup）

单选组：`plain` 圆点，或 `button` 大按钮卡片（对齐扫描页模式选择）。

```js
import RadioGroup from 'ui/input/radio';

<RadioGroup
  label="频率"
  value={v}
  onChange={(e) => setV(e.target.value)}
  options={[
    { value: 'd', label: '日' },
    { value: 'w', label: '周' },
  ]}
/>

<RadioGroup
  label="扫描模式"
  variant="button"
  value={mode}
  onChange={(e) => setMode(e.target.value)}
  options={[
    { value: 'strict', label: '严格模式', description: '依赖数据须更新至最新交易日。' },
    { value: 'demo', label: '扫描演示', description: '演示用，非实时市场。' },
  ]}
/>
```

`button` 默认横向；窄屏自动折成纵向。图与文字间距已收紧。
