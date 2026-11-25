const doc = {
  summary: '头像：图片或姓名首字母回退。会员条等业务组合属 L2，本组件只做圆形头像原语。',
  params: [
    {
      name: 'src',
      type: 'string',
      defaultValue: 'undefined',
      description: '图片 URL；加载失败回退到字母。',
    },
    {
      name: 'name',
      type: 'string',
      defaultValue: "''",
      description: '用于首字母与无障碍名称。',
    },
    {
      name: 'alt',
      type: 'string',
      defaultValue: "''",
      description: '覆盖 aria-label；默认用 name。',
    },
    {
      name: 'size',
      type: "'sm' | 'md' | 'lg'",
      defaultValue: "'md'",
      description: '24 / 32 / 44px。',
    },
  ],
  scenarios: [
    '顶栏会员条头像。',
    '列表行作者 / 操作者。',
  ],
  antiPatterns: [
    '不要把 Pro / 猫粮等业务信息塞进 Avatar（那是 member strip / L2）。',
  ],
};

export default doc;
