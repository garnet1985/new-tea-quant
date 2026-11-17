# separator

> 路径 `ui/text/separator`（图鉴 `/dev/ui/text#separator`）

分隔标题：左边文字（caption 字号/色），右边一根线。

```js
import Separator from 'ui/text/separator';

<Separator>行内特殊字形</Separator>
```

上下距默认 **1rem**：放进 `Section`（默认 gap）等堆叠容器即可，自身不设 margin。

编号大节标题（如「1. 形态」）用 `Heading` 即可，不必再加竖条。
