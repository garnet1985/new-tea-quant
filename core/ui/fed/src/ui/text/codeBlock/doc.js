const doc = {
  summary: '多行代码块。等宽展示；language 仅作标注。语法高亮（如 highlight.js）暂未接入。行内短代码请用 Text variant="code"。',
  params: [
    {
      name: 'language',
      type: 'string',
      defaultValue: "''",
      description: '语言标注（右上角）；暂不驱动高亮。',
    },
    {
      name: 'surface',
      type: "'none' | 'soft' | 'panel' | 'glass' | 'gradient'",
      defaultValue: "'panel'",
      description: '表面预设，与 Block 同源 token。',
    },
    {
      name: 'radius',
      type: "'none' | 'sm' | 'md' | 'lg' | 'pill'",
      defaultValue: "'md'",
      description: '圆角；pill 对代码块无意义，样式回落 lg。',
    },
    {
      name: 'padding',
      type: "'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '内边距。',
    },
    {
      name: 'bordered',
      type: 'boolean',
      defaultValue: 'true',
      description: '描边。',
    },
    {
      name: 'children',
      type: 'string | ReactNode',
      defaultValue: '—',
      description: '代码内容；字符串时保留换行。',
    },
  ],
  scenarios: [
    '文档 / 图鉴里展示多行片段。',
    '配置示例、错误堆栈只读展示。',
  ],
  antiPatterns: [
    '路径、单行键名用 Text variant="code"，不要用代码块。',
    '禁止在调用处写 fontFamily / fontSize px。',
    '现阶段不要依赖 language 做高亮。',
  ],
};

export default doc;
