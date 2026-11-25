const doc = {
  summary: '加载态组合原语：page / inline / inlineRow。内部用 loadingBars，文案用普通 p + .ntq-muted。',
  params: [
    {
      name: 'variant',
      type: "'page' | 'inline' | 'inlineRow'",
      defaultValue: "'inline'",
      description: '加载场景形态。',
    },
    {
      name: 'message',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '可选说明文案。',
    },
    {
      name: 'aria-label',
      type: 'string',
      defaultValue: '由 message 或「加载中」',
      description: '无障碍。',
    },
  ],
  scenarios: [
    '页面首屏：variant="page"。',
    '卡片/表格内：variant="inline"。',
    '工具条旁：variant="inlineRow"。',
  ],
  antiPatterns: [
    '禁止在调用处写死 minHeight 像素。',
  ],
};

export default doc;
