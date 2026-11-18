const doc = {
  summary: '块级容器原语。padding / gap / radius / surface 用语义 token。表面仅三档：透光玻璃 / 毛玻璃 / 渐变毛玻璃。',
  params: [
    {
      name: 'padding',
      type: "'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '内边距 token。',
    },
    {
      name: 'gap',
      type: "'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '子元素纵向间距；默认 1rem（--ntq-stack）。紧凑传 none。',
    },
    {
      name: 'radius',
      type: "'none' | 'sm' | 'md' | 'lg' | 'pill'",
      defaultValue: '未传：bordered→md，否则 none',
      description: '圆角。侧栏贴边常用 none；卡片 md/lg；胶囊 pill。',
    },
    {
      name: 'surface',
      type: "'none' | 'glass' | 'frost' | 'frost-strong' | 'soft' | 'panel' | 'gradient'",
      defaultValue: "'none'",
      description: 'glass=透光抬亮；frost=毛玻璃；frost-strong=渐变毛玻璃。旧名 soft/panel/gradient 仍可用。',
    },
    {
      name: 'bordered',
      type: 'boolean',
      defaultValue: 'false',
      description: '描边；可与 surface / radius 组合。',
    },
    {
      name: 'sticky',
      type: 'boolean',
      defaultValue: 'false',
      description: '是否 position:sticky 贴顶。侧栏整栏（标题+菜单）贴顶时用本项；仅菜单贴顶用 SideNav sticky。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '块内内容。',
    },
  ],
  scenarios: [
    'Column 某一列里包一组控件。',
    '普通列表外壳：surface="glass" radius="md" bordered。',
    '怕透底的表单/执行区：surface="frost"。',
    '报告 / 图表区：surface="frost-strong"。',
    '侧栏贴边贴顶：surface="frost" radius="none" sticky。',
  ],
  antiPatterns: [
    '禁止 padding={16} / gap="12px" / style 里写 borderRadius px。',
    '不要在 Block 上做业务标题行。',
    '不要再用 rgba(0,0,0,0.12) 黑压当表面；改 frost / frost-strong。',
  ],
};

export default doc;
