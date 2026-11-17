const doc = {
  summary: 'MetricCard 网格。窄屏默认 1 列；denseXs 时窄屏 2 列；宽屏按 columns=2/3/4。',
  params: [
    {
      name: 'columns',
      type: '2 | 3 | 4',
      defaultValue: '2',
      description: '≥900px 时的列数。',
    },
    {
      name: 'denseXs',
      type: 'boolean',
      defaultValue: 'false',
      description: '窄屏也用 2 列。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '通常为多个 MetricCard。',
    },
  ],
  scenarios: [
    '报告概览：两列指标卡。',
    '密集摘要：columns={4} 或 denseXs。',
  ],
  antiPatterns: [
    '不要用 MetricGrid 做整页版式（用 Column / Section）。',
    '不要在格子里塞表格（用 DataGrid）。',
  ],
};

export default doc;
