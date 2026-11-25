const doc = {
  summary: '标题原语。父级默认 gap=1rem；本组件再补上边距：md→视觉 1.5rem，lg→视觉 2rem；下边距仍为 1rem（父 gap）。',
  params: [
    {
      name: 'level',
      type: "'h1' | 'h2' | 'h3' | 'h4' | 'h5'",
      defaultValue: "'h2'",
      description: '语义标签与字号阶梯。',
    },
    {
      name: 'variant',
      type: "'plain' | 'bar'",
      defaultValue: "'plain'",
      description: 'plain 无装饰；bar 左侧竖条。',
    },
    {
      name: 'tone',
      type: "'cyan' | 'violet' | 'green' | 'warning' | 'error' | 'muted'",
      defaultValue: "'cyan'",
      description: '仅 variant="bar" 时的竖条色。',
    },
    {
      name: 'subtitle',
      type: 'string',
      defaultValue: "''",
      description: '副标题。',
    },
    {
      name: 'subtitlePlacement',
      type: "'below' | 'inline'",
      defaultValue: "'below'",
      description: '副标题位置。',
    },
    {
      name: 'gap',
      type: "'none' | 'md' | 'lg'",
      defaultValue: "'md'",
      description: '在父级 1rem gap 上补上边距：md=+0.5→1.5；lg=+1→2；none=不补。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '主标题文案。',
    },
  ],
  scenarios: [
    '正文流里的章节标题：默认 gap="md"。',
    '更强分隔：gap="lg"。',
    '侧栏紧凑：gap="none"。',
  ],
  antiPatterns: [
    '不要在子项上再叠 margin-block 与父级 gap 混用。',
    '禁止手写 margin px；改 --ntq-stack / --ntq-heading-margin-*。',
  ],
};

export default doc;
