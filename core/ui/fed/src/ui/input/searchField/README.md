# searchField

搜索输入（前缀 search 图标）。默认无 Field 标签，适合列表/工具栏过滤。

**不要并进 TextField**——场景不同：检索 vs 表单短文本。

```js
import SearchField from 'ui/input/searchField';

<SearchField value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索策略" />
<SearchField fluid clearable label="关键词" labelPlacement="above" />
```

对齐旧 `views/searchField`（默认更宽约 360px；`fluid` 弹性宽）。
