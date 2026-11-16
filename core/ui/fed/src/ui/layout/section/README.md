# section

> 路径 `ui/layout/section`

纵向分区。**默认 `gap="md"` = 1rem（`--ntq-stack`）**。块距只走 gap，子项不要再叠上下 margin。

```js
// ✅
<Section>
  <p>一段</p>
  <Heading level="h2">标题</Heading>
  <p>下一段</p>
</Section>

<Section gap="none">紧凑</Section>

// ❌
<Section gap={24} />
```
