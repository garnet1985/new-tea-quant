const doc = {
  summary: '顶栏会员条展示壳。已登录：头像 / 名 / Pro / 猫粮或点数；未登录：提示 + 注册或设置链。',
  params: [
    { name: 'signedIn', type: 'boolean', defaultValue: 'false', description: '是否已登录。' },
    { name: 'name', type: 'string', defaultValue: "''", description: '显示名。' },
    { name: 'avatar', type: 'string', defaultValue: "''", description: '头像 URL。' },
    { name: 'isPro', type: 'boolean', defaultValue: 'false', description: '显示 ProBadge。' },
    { name: 'catfoodText', type: 'string|null', defaultValue: 'null', description: '猫粮文案；有则优先于点数。' },
    { name: 'points', type: 'number|null', defaultValue: 'null', description: '无猫粮时显示点数。' },
    { name: 'guestReason', type: "'unreachable'|'rejected'|其他", defaultValue: "''", description: '未登录提示类型。' },
    { name: 'registerUrl', type: 'string', defaultValue: "''", description: '成为会员外链。' },
    { name: 'membershipTo', type: 'string', defaultValue: "'/settings/membership'", description: '会员设置路由。' },
  ],
  scenarios: [
    'AppNavigation 挂角。',
  ],
  antiPatterns: [
    '不要在本组件里 fetch 会员资料。',
    'Pro 样式用 ProBadge，不要复制彩虹 SCSS。',
  ],
};

export default doc;
