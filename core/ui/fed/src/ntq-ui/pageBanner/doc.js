const doc = {
  summary: 'NTQ 页头 Banner：大标题 + 可选说明与右侧操作槽。列宽由外层 content 约束。',
  params: [
    {
      name: 'title',
      type: 'ReactNode',
      defaultValue: '—',
      description: '页头主标题。',
    },
    {
      name: 'description',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '标题下说明（可用 muted / code）。',
    },
    {
      name: 'rightSlot',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '右侧操作区（按钮等）。',
    },
  ],
  scenarios: [
    '列表页 / 设置页顶部标题条。',
    '右侧放刷新、新建等操作。',
  ],
  antiPatterns: [
    '全局告警通栏用 Message variant="banner"。',
    '区块小节标题用 Heading，不要用 PageBanner。',
  ],
};

export default doc;
