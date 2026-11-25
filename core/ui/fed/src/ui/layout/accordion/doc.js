const doc = {
  summary: '折叠区块。panel=顶层拼缝；nested=内嵌圆角卡片。收起时仍挂载子树，避免表单态丢失。',
  params: [
    {
      name: 'title',
      type: 'ReactNode',
      defaultValue: '—',
      description: '标题行文案。',
    },
    {
      name: 'tooltip',
      type: 'string',
      defaultValue: "''",
      description: '标题旁 HelpTooltip；空则不渲染。',
    },
    {
      name: 'shine',
      type: 'boolean',
      defaultValue: 'false',
      description: 'tooltip 是否 shine。',
    },
    {
      name: 'variant',
      type: "'panel' | 'nested'",
      defaultValue: "'panel'",
      description: '顶层拼缝 / 内嵌卡片。',
    },
    {
      name: 'defaultExpanded',
      type: 'boolean',
      defaultValue: 'false',
      description: '非受控初始展开。',
    },
    {
      name: 'expanded',
      type: 'boolean',
      defaultValue: '—',
      description: '受控展开态。',
    },
    {
      name: 'onExpandedChange',
      type: '(open: boolean) => void',
      defaultValue: '—',
      description: '展开变化回调。',
    },
  ],
  scenarios: [
    '策略设置 / 系统设置等分组折叠。',
    '表单内嵌二级折叠（variant="nested"）。',
  ],
  antiPatterns: [
    '不要用 Accordion 当普通 Section 标题（无需折叠时用 Section / Heading）。',
    '不要假设收起会卸载子树；需要卸载时自行条件渲染 children。',
  ],
};

export default doc;
