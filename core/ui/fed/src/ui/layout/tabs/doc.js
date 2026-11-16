const doc = {
  summary: '布局 Tab：variant="top" 上方切换内容；variant="side" 左右分栏（左导航右内容）。用 items 描述页签与内容。',
  params: [
    {
      name: 'variant',
      type: "'top' | 'side'",
      defaultValue: "'top'",
      description: '上方横排，或左侧竖排导航。',
    },
    {
      name: 'items',
      type: 'Array<{ id, label, content?, disabled? }>',
      defaultValue: '[]',
      description: '页签列表；content 为对应面板内容。',
    },
    {
      name: 'value',
      type: 'string',
      defaultValue: '—',
      description: '受控当前 id。',
    },
    {
      name: 'defaultValue',
      type: 'string',
      defaultValue: '首项 id',
      description: '非受控初始 id。',
    },
    {
      name: 'onChange',
      type: '(id: string) => void',
      defaultValue: '—',
      description: '切换回调。',
    },
    {
      name: 'gap',
      type: "'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '页签列表与内容区间距（默认 1rem）。',
    },
  ],
  scenarios: [
    '设置页 / 详情页：variant="side"。',
    '区块内切换子视图：variant="top"。',
  ],
  antiPatterns: [
    '不要用 Tabs 做页面主导航（用路由侧栏）。',
    '不要在 items 外再套一层手写 tab 按钮。',
    '禁止 gap 写裸 px。',
  ],
};

export default doc;
