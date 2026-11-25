const doc = {
  summary: '竖条加载动画。size 只选 sm/md；条数固定，不开放数字 barCount。',
  params: [
    {
      name: 'size',
      type: "'md' | 'sm'",
      defaultValue: "'md'",
      description: '条高度/粗细预设。',
    },
    {
      name: 'aria-label',
      type: 'string',
      defaultValue: "'加载中'",
      description: '无障碍文案。',
    },
  ],
  scenarios: [
    '单独作轻量 loading 指示。',
    '被 Loading（page/inline）组合使用。',
  ],
  antiPatterns: [
    '禁止 barCount={7}。',
    '整页占位请用 Loading variant="page"。',
  ],
};

export default doc;
