const doc = {
  summary: '统一说明 Tooltip（对齐 app）：help / info / warning 触发图标 + 气泡 + 可选 shine + 浮入动画。图标固定 md；无 title 不渲染。',
  params: [
    {
      name: 'title',
      type: 'ReactNode',
      defaultValue: '—',
      description: '气泡内容；空则不渲染。',
    },
    {
      name: 'variant',
      type: "'help' | 'info' | 'warning'",
      defaultValue: "'help'",
      description: '触发图标形态。',
    },
    {
      name: 'shine',
      type: 'boolean',
      defaultValue: 'false',
      description: '图标扫光动画（强调可点提示）。',
    },
    {
      name: 'placement',
      type: 'MUI Tooltip placement',
      defaultValue: "'top'",
      description: '气泡方位，如 top / bottom / left / right 及 *-start / *-end。',
    },
    {
      name: 'ariaLabel',
      type: 'string',
      defaultValue: '按 variant 默认中文',
      description: '触发器无障碍标签。',
    },
  ],
  scenarios: [
    '表单字段旁补充说明。',
    '列表标题旁展示简介。',
    '需要引起注意的提示：variant="warning" 或 shine。',
  ],
  antiPatterns: [
    '不要给本组件加 size / iconSize（固定 md）。',
    '不要用本组件替代按钮上的简短 tooltip（按钮用 NtqButton.tooltip）。',
    '不要在无说明文案时强行挂空 title。',
  ],
};

export default doc;
