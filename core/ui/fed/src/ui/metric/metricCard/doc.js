const doc = {
  summary: '报告指标卡：标题 + 主值 + 可选 hint；标题旁可用 tip（HelpTooltip）。常与 MetricGrid 一起用。',
  params: [
    {
      name: 'title',
      type: 'ReactNode',
      defaultValue: '—',
      description: '指标名。',
    },
    {
      name: 'value',
      type: 'ReactNode',
      defaultValue: '—',
      description: '主数值或短文案。',
    },
    {
      name: 'hint',
      type: 'ReactNode',
      defaultValue: 'undefined',
      description: '主值下方次要说明（如占比）。',
    },
    {
      name: 'tip',
      type: 'ReactNode',
      defaultValue: 'undefined',
      description: '标题旁帮助气泡。优先于 titleTip。',
    },
    {
      name: 'titleTip',
      type: 'ReactNode',
      defaultValue: 'undefined',
      description: '兼容旧 API；等同 tip。',
    },
  ],
  scenarios: [
    '回测 / 枚举报告：机会总数、完整度、涨跌停占比。',
    '与 MetricGrid 组成 2/3/4 列指标区。',
  ],
  antiPatterns: [
    '不要把大段说明塞进 value（用 hint 或正文）。',
    '不要用 MetricCard 做可点筛选（用 CountTab / 按钮）。',
  ],
};

export default doc;
