const doc = {
  summary: 'NTQ 页头 Banner（占位）。计划迁自 views/pageBanner：title / description / rightSlot。',
  params: [
    {
      name: 'title',
      type: 'string',
      defaultValue: '—',
      description: '页头标题（实现后）。',
    },
    {
      name: 'description / rightSlot',
      type: 'ReactNode',
      defaultValue: '—',
      description: '副文案与右侧操作区（实现后）。',
    },
  ],
  scenarios: [
    '列表页 / 设置页顶部标题条。',
  ],
  antiPatterns: [
    '全局告警通栏用 Message variant="banner"。',
  ],
};

export default doc;
