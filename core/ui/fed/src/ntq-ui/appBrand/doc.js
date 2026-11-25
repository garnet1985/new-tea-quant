const doc = {
  summary: 'NTQ 品牌标：徽标 + 彩虹字名称 + 可选 version。属应用壳，不是通用 logo。',
  params: [
    {
      name: 'to',
      type: 'string',
      defaultValue: "'/welcome'",
      description: '点击跳转路径。',
    },
    {
      name: 'name',
      type: 'string',
      defaultValue: "'New Tea Quant'",
      description: '品牌文案。',
    },
    {
      name: 'logoSrc',
      type: 'string',
      defaultValue: "'/logo.png'",
      description: '徽标图；失败回退 tactic 图标。',
    },
    {
      name: 'version',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '名称下方版本槽（如 AppVersion）。',
    },
    {
      name: 'linkComponent',
      type: 'Component',
      defaultValue: 'RouterLink',
      description: '链接组件；图鉴可传 DemoLink。',
    },
  ],
  scenarios: [
    '顶栏左侧品牌入口。',
  ],
  antiPatterns: [
    '欢迎页大图英雄区不要硬套本组件（布局不同）。',
    '图鉴勿再套 MemoryRouter。',
  ],
};

export default doc;
