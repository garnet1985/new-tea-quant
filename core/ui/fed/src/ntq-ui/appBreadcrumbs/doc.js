const doc = {
  summary: 'NTQ 面包屑。祖先链可点（RouterLink）；current 为当前页不可点。属应用壳，不是通用 layout。',
  params: [
    {
      name: 'items',
      type: "{ label: string, to: string }[]",
      defaultValue: '[]',
      description: '从根到上一层的可点节点。',
    },
    {
      name: 'current',
      type: 'ReactNode',
      defaultValue: '—',
      description: '当前页文案（aria-current=page）。',
    },
    {
      name: 'linkComponent',
      type: 'Component',
      defaultValue: 'RouterLink',
      description: '祖先链链接组件；图鉴可传入阻止跳转的 DemoLink。',
    },
  ],
  scenarios: [
    '详情页：策略 → 某策略名。',
    '设置子页：设置 → 会员。',
  ],
  antiPatterns: [
    '页面内局部切换用 Tabs，不要用面包屑。',
    '不要把业务路由表写死在本组件（items 由页面传入）。',
    '图鉴里不要再套 MemoryRouter（外层已有 Router）。',
  ],
};

export default doc;
