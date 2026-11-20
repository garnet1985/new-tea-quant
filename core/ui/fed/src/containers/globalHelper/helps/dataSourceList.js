/** 数据源列表：`/advanced/data-sources` */
export function matchDataSourceList(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  return path === '/advanced/data-sources';
}

export const DATA_SOURCE_LIST_HELP = {
  id: 'data-source-list',
  version: 1,
  trigger: 'enter',
  match: matchDataSourceList,
  steps: [
    {
      pages: [
        {
          title: '数据源',
          body: '「数据源」是连接并获取第三方数据的入口。系统默认使用 NTQ 自带的演示数据，目前大约只有三年历史。',
        },
      ],
    },
    {
      target: 'data-source-list-providers',
      pages: [
        {
          title: '数据来源',
          body: '这里标明该数据由哪个供应商提供。',
        },
      ],
    },
    {
      target: 'data-source-list-status',
      pages: [
        {
          title: '数据状态',
          body: '这里可以看到当前数据源是否已经更新到最新，以及是否需要再拉一次。',
        },
      ],
    },
    {
      target: 'data-source-list-origin',
      pages: [
        {
          title: '来源',
          body: '区分这项数据是系统自带，还是你自己扩展接入的。',
        },
      ],
    },
    {
      target: 'data-source-list-renew-type',
      pages: [
        {
          title: '更新方式',
          body: '说明该项数据按什么方式续传或刷新，例如增量续传等。',
        },
      ],
    },
    {
      target: 'data-source-list-rate-limit',
      pages: [
        {
          title: '限速',
          body: '显示供应商 API 的每分钟限速。拉取时会按该值自动限流，避免触发供应商限制。',
        },
      ],
    },
    {
      target: 'data-source-list-auth',
      pages: [
        {
          title: '认证',
          body: '标明当前供应商是否需要认证，以及认证是否已经可用。需要 Token 却未配置时，通常无法更新。',
        },
      ],
    },
  ],
};
