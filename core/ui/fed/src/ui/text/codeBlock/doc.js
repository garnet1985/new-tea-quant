const doc = {
  summary: '多行代码块。默认科技玻璃；变种 soft。language 落在上内边距带内，不与代码重叠。语法高亮暂未接入。',
  params: [
    {
      name: 'variant',
      type: "'glass' | 'soft'",
      defaultValue: "'glass'",
      description: 'glass：科技玻璃（默认）；soft：轻底无模糊。',
    },
    {
      name: 'language',
      type: 'string',
      defaultValue: "''",
      description: '右上角语言标注；占用上内边距，不驱动高亮。',
    },
    {
      name: 'children',
      type: 'string | ReactNode',
      defaultValue: '—',
      description: '代码内容；字符串时保留换行。',
    },
  ],
  scenarios: [
    '文档 / 图鉴展示多行片段：默认 glass。',
    '嵌在已有玻璃面板里时可用 soft，避免双重模糊。',
  ],
  antiPatterns: [
    '不要再传 surface / radius / padding / bordered；样式只走 variant。',
    '路径、单行键名用 Text variant="code"。',
    '现阶段不要依赖 language 做高亮。',
  ],
};

export default doc;
