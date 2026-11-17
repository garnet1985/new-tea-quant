const doc = {
  summary: '报告区块固定模板：描边浅底 + 标题/tip/action + 内容。回测报告统一用本壳，避免各页自造 SectionBlock。',
  params: [
    {
      name: 'title',
      type: 'ReactNode',
      defaultValue: '—',
      description: '区块标题。',
    },
    {
      name: 'tip',
      type: 'ReactNode',
      defaultValue: 'undefined',
      description: '标题旁 HelpTooltip。',
    },
    {
      name: 'action',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '标题行右侧操作（按钮等）。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '内容：MetricGrid / ChartPanel / 文案等。',
    },
  ],
  scenarios: [
    '机会盘点 / 涨跌停 / 资金分配等报告小节。',
  ],
  antiPatterns: [
    '不要手写一套报告边框；用本组件。',
    '不要在 ReportBlock 上再叠业务 Metric 映射（用 MetricCard）。',
    '页面大标题用 PageBanner / Heading，不要用 ReportBlock。',
  ],
};

export default doc;
