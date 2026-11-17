const doc = {
  summary: '归类过滤条：固定「全部」CountTab + 横向滚动归类 chips。过滤状态由页面持有。',
  params: [
    {
      name: 'all',
      type: '{ label, count, selected, onClick, title?, disabled? }',
      defaultValue: '—',
      description: '「全部」宽 Tab。',
    },
    {
      name: 'items',
      type: 'Array<{ key, label, count, selected, onClick, title?, disabled? }>',
      defaultValue: '[]',
      description: '归类 chips；选中项可挂 selectedItemRef。',
    },
    {
      name: 'selectedItemRef',
      type: 'Ref',
      defaultValue: 'null',
      description: '滚入视野用：挂到当前 selected 的 CountTab。',
    },
    {
      name: 'ariaLabel',
      type: 'string',
      defaultValue: "'按归类筛选'",
      description: 'role=group 的无障碍名。',
    },
  ],
  scenarios: [
    '策略列表 / 扫描列表按归类筛选。',
  ],
  antiPatterns: [
    '不要在本组件内解析 URL query；由页面读写。',
    '单枚 CountTab 请直接用 CountTab，不必包一层。',
  ],
};

export default doc;
