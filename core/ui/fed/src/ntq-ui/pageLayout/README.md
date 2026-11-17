# pageLayout

标准页壳：`AppBreadcrumbs` + `PageBanner` + 正文。

```js
import PageLayout from 'ntq-ui/pageLayout';

<PageLayout
  breadcrumbsItems={[{ label: '制定策略', to: '/strategy-design' }]}
  breadcrumbsCurrent="设置"
  bannerTitle="设置"
>
  …
</PageLayout>
```
