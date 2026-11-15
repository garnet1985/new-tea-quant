const doc = {
  summary: '引用块（固定样式）：左侧白竖条 + 轻白底 + 四面缩进 + 斜体。无 size / padding / color 变体。说明/提示用 TextBlock。',
  params: [
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '引用正文（可用段落）。',
    },
  ],
  scenarios: [
    '摘录设计原则、他人原话、文档金句。',
  ],
  antiPatterns: [
    '不要给 Quote 加 padding / tone / size 等变体 props。',
    '不要用 Quote 冒充警告/摘要（用 TextBlock）。',
    '不要用 Quote 当标题（用 Heading）。',
  ],
};

export default doc;
