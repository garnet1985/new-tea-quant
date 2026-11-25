const doc = {
  summary: '说明性文本块：左侧竖条 + 可选表面。用于摘要、提示、反例列表等。标题请用 Heading。',
  params: [
    {
      name: 'bar',
      type: "'cyan' | 'violet' | 'green' | 'warning' | 'error' | 'muted'",
      defaultValue: "'cyan'",
      description: '左侧竖条颜色。',
    },
    {
      name: 'surface',
      type: "'none' | 'soft' | 'panel' | 'glass' | 'gradient'",
      defaultValue: "'soft'",
      description: '表面背景。',
    },
    {
      name: 'radius',
      type: "'none' | 'sm' | 'md' | 'lg' | 'pill'",
      defaultValue: "'md'",
      description: '右侧圆角（左侧贴齐竖条）。',
    },
    {
      name: 'padding',
      type: "'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '内边距。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '段落、列表等说明内容。',
    },
  ],
  scenarios: [
    '组件摘要说明：bar="cyan" surface="soft"。',
    '警告 / 反例列表：bar="warning"。',
  ],
  antiPatterns: [
    '不要用 TextBlock 当标题；标题用 Heading variant="bar"。',
    '上方已有带竖条 Heading 时，下方不必再套竖条 TextBlock。',
  ],
};

export default doc;
