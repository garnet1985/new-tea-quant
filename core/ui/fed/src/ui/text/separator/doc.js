const doc = {
  summary: '分隔标题：左侧文案用 caption 字号与色，右侧横线。编号大节用 Heading，不必加竖条。',
  params: [
    {
      name: 'tone',
      type: "'default' | 'muted'",
      defaultValue: "'default'",
      description: '文案与线条强弱。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '左侧标题文案。',
    },
  ],
  scenarios: [
    '图鉴样本行标签。',
    '文档里小节分隔。',
  ],
  antiPatterns: [
    '不要用 Separator 替代页面主标题（用 Heading）。',
    '「1. 形态」这类编号标题用 Heading，不要再加 bar。',
  ],
};

export default doc;
