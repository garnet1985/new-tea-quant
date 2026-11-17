const doc = {
  summary: '圆形计数角标。用于行内 / 标题旁展示数量；不是可点的筛选 Tab。',
  params: [
    {
      name: 'count',
      type: 'ReactNode',
      defaultValue: '—',
      description: '显示的数字或内容。',
    },
    {
      name: 'label',
      type: 'string',
      defaultValue: 'undefined',
      description: '无障碍名称（aria-label），如「信号数」。',
    },
  ],
  scenarios: [
    '列表行：信号数 / 子项数。',
    '标题旁静态计数。',
  ],
  antiPatterns: [
    '可点击归类筛选用 CountTab，不要用 CountBadge。',
    '状态文案用 Tag，不要塞进 CountBadge。',
  ],
};

export default doc;
