const doc = {
  summary: '列表工具条：搜索槽 + 操作按钮槽 + 可选尾部提示。过滤逻辑与按钮行为由页面提供。',
  params: [
    {
      name: 'search',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '通常放 SearchField（fluid + glass）。',
    },
    {
      name: 'actions',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '刷新 / 新建 / 导入等 Button 组合。',
    },
    {
      name: 'hint',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '靠右弱提示文案（自动 margin-left: auto）。',
    },
  ],
  scenarios: [
    '数据源 / Tag / 策略 / 扫描等列表页顶栏。',
  ],
  antiPatterns: [
    '不要把表格本身塞进 ListToolbar。',
    '不要在本组件内写死业务 API 调用。',
  ],
};

export default doc;
