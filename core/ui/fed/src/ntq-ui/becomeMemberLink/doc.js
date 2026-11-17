const doc = {
  summary: '「成为会员」注册入口壳。href 由应用传入；不 fetch 站点 URL。',
  params: [
    { name: 'href', type: 'string', defaultValue: "''", description: '注册页外链；空则不渲染。' },
    { name: 'label', type: 'string', defaultValue: "'成为会员'", description: '文案。' },
    {
      name: 'variant',
      type: "'button' | 'link'",
      defaultValue: "'button'",
      description: '玻璃按钮或行内文字链（均带外链示意）。',
    },
  ],
  scenarios: [
    '设置 → 会员：未装载凭证时引导注册。',
    '引导 / 欢迎页注册入口。',
  ],
  antiPatterns: [
    '不要在本组件里 fetchSiteUrls / 写死官网 URL。',
    '不要再引用 views/becomeMemberLink（已迁至此）。',
  ],
};

export default doc;
