const doc = {
  summary: '标题原语。level 决定 h1–h5 与固定字号；variant=bar 为官网式左竖条；可副标题（below/inline）；gap 控制上>下>段落的外边距。',
  params: [
    {
      name: 'level',
      type: "'h1' | 'h2' | 'h3' | 'h4' | 'h5'",
      defaultValue: "'h2'",
      description: '语义标签与字号阶梯；字号不可用 size 覆盖。',
    },
    {
      name: 'variant',
      type: "'plain' | 'bar'",
      defaultValue: "'plain'",
      description: 'plain 无装饰；bar 左侧竖条 + 左/上下内边距（无背景）。',
    },
    {
      name: 'tone',
      type: "'cyan' | 'violet' | 'green' | 'warning' | 'error' | 'muted'",
      defaultValue: "'cyan'",
      description: '仅 variant="bar" 时生效的竖条色。',
    },
    {
      name: 'subtitle',
      type: 'string',
      defaultValue: "''",
      description: '副标题，字号更小、颜色 muted。',
    },
    {
      name: 'subtitlePlacement',
      type: "'below' | 'inline'",
      defaultValue: "'below'",
      description: '副标题在下方或与主标题同一行。',
    },
    {
      name: 'gap',
      type: "'none' | 'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '上下外边距档位；永远上 > 下 > 普通段落间距。none 用于侧栏等紧凑处。',
    },
    {
      name: 'as',
      type: 'ElementType',
      defaultValue: '与 level 同名',
      description: '覆盖语义标签（少用）。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '主标题文案。',
    },
  ],
  scenarios: [
    '页面主标题：level="h1"。',
    '官网式章节：variant="bar" tone="cyan|warning"。',
    '副标题：subtitle + subtitlePlacement。',
    '侧栏：gap="none"。',
  ],
  antiPatterns: [
    '禁止用 style/fontSize 改标题大小；只改 level。',
    '禁止手写 margin px；改 --ntq-heading-gap-*。',
    '正文说明用 p / .ntq-muted，不要用 Heading 缩小冒充。',
  ],
};

export default doc;
