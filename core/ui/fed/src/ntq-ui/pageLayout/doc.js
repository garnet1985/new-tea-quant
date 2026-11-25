const doc = {
  summary: '标准页壳：面包屑 + Banner + 正文；loading 时用 Loading page。',
  params: [
    { name: 'breadcrumbsItems', type: '{ label, to }[]', defaultValue: '[]', description: '祖先链。' },
    { name: 'breadcrumbsCurrent', type: 'ReactNode', defaultValue: '—', description: '当前页。' },
    { name: 'bannerTitle', type: 'ReactNode', defaultValue: '—', description: 'Banner 标题。' },
    { name: 'bannerDescription', type: 'ReactNode', defaultValue: 'null', description: 'Banner 说明。' },
    { name: 'bannerRightSlot', type: 'ReactNode', defaultValue: 'null', description: 'Banner 右侧。' },
    { name: 'loading', type: 'boolean', defaultValue: 'false', description: '整页加载态。' },
    { name: 'showBreadcrumbs', type: 'boolean', defaultValue: 'true', description: '是否显示面包屑。' },
    { name: 'showBanner', type: 'boolean', defaultValue: 'true', description: '是否显示 Banner。' },
  ],
  scenarios: [
    '设置 / 列表 / 详情等标准业务页。',
  ],
  antiPatterns: [
    '不要在页面里再手拼一套面包屑+大标题。',
  ],
};

export default doc;
