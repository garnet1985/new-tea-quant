const doc = {
  summary: '块级容器原语。padding / gap / radius / surface 用语义 token；可做软底、玻璃模糊、渐变与胶囊圆角。',
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
      defaultValue: "'none'",
      description: '子元素纵向间距 token。',
    },
    {
      name: 'radius',
      type: "'none' | 'sm' | 'md' | 'lg' | 'pill'",
      defaultValue: '未传：bordered→md，否则 none',
      description: '圆角。侧栏贴边常用 none；卡片 md/lg；胶囊 pill。',
    },
    {
      name: 'surface',
      type: "'none' | 'soft' | 'panel' | 'glass' | 'gradient'",
      defaultValue: "'none'",
      description: '表面：透明 / 浅底 / 稍实底 / 玻璃模糊 / 纵向浅渐变。',
    },
    {
      name: 'bordered',
      type: 'boolean',
      defaultValue: 'false',
      description: '描边；可与 surface / radius 组合。',
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
    '卡片：surface="soft|gradient" radius="md" bordered。',
    '玻璃浮层：surface="glass" radius="lg"。',
    '侧栏贴边：surface="panel" radius="none"。',
  ],
  antiPatterns: [
    '禁止 padding={16} / gap="12px" / style 里写 borderRadius px。',
    '不要在 Block 上做业务标题行。',
  ],
};

export default doc;
