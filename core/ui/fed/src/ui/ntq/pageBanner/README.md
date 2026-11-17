# pageBanner

NTQ 页头 Banner。

```js
import PageBanner from 'ui/ntq/pageBanner';

<PageBanner
  title="策略列表"
  description="管理已导入的策略包。"
  rightSlot={<NtqButton icon="refresh">刷新</NtqButton>}
/>
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `title` | — | 主标题 |
| `description` | `null` | 说明 |
| `rightSlot` | `null` | 右侧操作 |
