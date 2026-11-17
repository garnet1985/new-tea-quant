const doc = {
  summary: '带计数的筛选 Tab。用于列表工具栏「全部 / 归类」等；选中态高亮，过滤逻辑由上层对 rows 处理。',
  params: [
    {
      name: 'label',
      type: 'ReactNode',
      defaultValue: '—',
      description: 'Tab 文案。',
    },
    {
      name: 'count',
      type: 'number | string',
      defaultValue: 'undefined',
      description: '有则显示为「label count」；省略则只显示 label。',
    },
    {
      name: 'selected',
      type: 'boolean',
      defaultValue: 'false',
      description: '选中态（aria-pressed + 青色描边/底）。',
    },
    {
      name: 'wide',
      type: 'boolean',
      defaultValue: 'false',
      description: 'true 时不限制 max-width（如「全部」）。',
    },
    {
      name: 'onClick',
      type: '() => void',
      defaultValue: 'undefined',
      description: '点击回调；上层切换 filter / query。',
    },
    {
      name: 'title',
      type: 'string',
      defaultValue: 'undefined',
      description: '原生 title（长标签悬停全文）。',
    },
    {
      name: 'disabled',
      type: 'boolean',
      defaultValue: 'false',
      description: '禁用。',
    },
  ],
  scenarios: [
    '策略 / 扫描列表：全部 + 横向滚动归类 Tab。',
    '需 scrollIntoView 时用 ref 接到选中项。',
  ],
  antiPatterns: [
    '不要把 filter 谓词写进 CountTab（上层算 displayRows）。',
    '不要用 CountTab 当普通状态 Tag（用 Tag）。',
    '不要用 CountTab 当页签切换整页内容（用 Tabs）。',
  ],
};

export default doc;
