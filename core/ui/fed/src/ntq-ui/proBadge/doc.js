const doc = {
  summary: 'Pro 彩虹描边小徽章。会员条等复用；不内置会员逻辑。',
  params: [
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: "'Pro'",
      description: '徽章文案。',
    },
  ],
  scenarios: [
    '顶栏会员条已登录且 is_pro。',
  ],
  antiPatterns: [
    '不要在业务里复制彩虹描边 SCSS。',
  ],
};

export default doc;
