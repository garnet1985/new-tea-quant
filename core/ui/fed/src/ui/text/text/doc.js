const doc = {
  summary: '行内特殊字形：code（等宽青色，无底无边）/ rainbow（品牌渐变）/ accent（青色强调）。普通正文 / 链接用 HTML + class（.ntq-muted / .ntq-link）；多行代码用 CodeBlock。',
  params: [
    {
      name: 'variant',
      type: "'code' | 'rainbow' | 'accent'",
      defaultValue: "'code'",
      description: '行内代码（mono + cyan）、彩虹字、强调字。',
    },
    {
      name: 'as',
      type: 'ElementType',
      defaultValue: 'code / span',
      description: '覆盖标签。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '文案。',
    },
  ],
  scenarios: [
    '路径、键名、短代码：variant="code"。',
    '品牌强调短词：variant="rainbow"。',
    '句中青色强调：variant="accent"。',
    '导航 / 外链：<a className="ntq-link">，可嵌 Icon size="sm"。',
  ],
  antiPatterns: [
    '不要用 Text 包每一段普通正文。',
    '不要做 Link 组件；用 .ntq-link。',
    '多行代码用 CodeBlock，不要用 variant="code" 硬撑。',
    '整页标题用 Heading。',
    "禁止 style={{ fontSize: '14px' }}。",
  ],
};

export default doc;
