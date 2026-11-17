const doc = {
  summary: '左侧目录壳：竖排可点项 + 选中态。栏宽用 Column sidebar；右栏内容自管（Outlet / 面板）。同页切内容优先 Tabs side。',
  params: [
    {
      name: 'items',
      type: '{ id, label, to?, href?, meta?, disabled? }[]',
      defaultValue: '[]',
      description: '目录项。to=站内；href=外链；都无则 button + onItemClick。meta 显示在右侧（如数量）。',
    },
    {
      name: 'activeId',
      type: 'string',
      defaultValue: "''",
      description: '当前选中项 id。',
    },
    {
      name: 'variant',
      type: "'line' | 'rail'",
      defaultValue: "'line'",
      description: 'line=底边选中条（图鉴）；rail=左侧色条高亮当前项（设置页；窄屏改底边条）。',
    },
    {
      name: 'radius',
      type: "'sm' | 'none'",
      defaultValue: "'sm'",
      description: '扩展：sm=rail 项小圆角（默认）；none=直角。',
    },
    {
      name: 'sticky',
      type: 'boolean',
      defaultValue: 'false',
      description: '是否 position:sticky 贴顶（max-height 100vh + 内部滚动）。整栏含标题贴顶时用外层 Block sticky，本项保持 false。',
    },
    {
      name: 'linkComponent',
      type: 'Component',
      defaultValue: 'RouterLink',
      description: '站内链组件。',
    },
    {
      name: 'onItemClick',
      type: '(id, event?) => void',
      defaultValue: 'undefined',
      description: '点击回调（无 to 的项或额外逻辑）。',
    },
  ],
  scenarios: [
    '图鉴 / 文档站：Column sidebar + SideNav variant=line + Outlet。',
    '设置类：variant=rail；或直接用 Tabs side 连内容面板。',
  ],
  antiPatterns: [
    '全站主导航用 AppNav，不要用 SideNav。',
    '同页切 panel 且内容跟 tab 绑死 → 用 Tabs variant="side"。',
    '不要把路由表写死进 SideNav。',
  ],
};

export default doc;
