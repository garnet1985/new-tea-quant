const doc = {
  summary: 'NTQ 顶栏导航壳。items 由应用传入（站内 to / 外链 href / children 下拉）；不内置路由表、不拉站点 API。',
  params: [
    {
      name: 'items',
      type: 'NavItem[]',
      defaultValue: '[]',
      description: '导航项。站内：{ label, to, icon?, match? }；外链：{ label, href, icon? }；下拉：{ label, icon?, match?, children: [{ label, to }] }。',
    },
    {
      name: 'pathname',
      type: 'string',
      defaultValue: '跟 Router；未在 Router 内则为空',
      description: '显式传入时不再调用 useLocation（图鉴演示激活态用这个，勿套 MemoryRouter）。',
    },
    {
      name: 'linkComponent',
      type: 'Component',
      defaultValue: 'RouterLink',
      description: '站内链组件；需接受 to / className / children。',
    },
  ],
  scenarios: [
    '应用顶栏：主入口 + 高级下拉 + 文档外链 + 设置。',
    '图鉴：pathname + linkComponent 演示，勿再套 MemoryRouter。',
  ],
  antiPatterns: [
    '页面内局部 Tab 用 ui/layout/tabs。',
    '不要在本组件里写死产品路由或 fetchSiteUrls（那是应用组装层）。',
  ],
};

export default doc;
