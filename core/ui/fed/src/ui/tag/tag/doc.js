const doc = {
  summary: '标签 / 状态小块。通用原语；业务 status→色/形态映射放第二层（不进本组件）。',
  params: [
    {
      name: 'status',
      type: "'success' | 'error' | 'warning' | 'info' | 'neutral'",
      defaultValue: "'neutral'",
      description: '语义状态色。与 color 二选一；有 color 则走颜色模式。',
    },
    {
      name: 'color',
      type: "'green' | 'error' | 'warning' | 'muted' | 'cyan' | 'violet'",
      defaultValue: 'undefined',
      description: '装饰色（含紫）。有 color 时忽略 status。',
    },
    {
      name: 'variant',
      type: "'soft' | 'outline' | 'solid'",
      defaultValue: "'soft'",
      description: 'soft=描边+半透明底；outline=仅描边；solid=border 与背景同色实心。',
    },
    {
      name: 'size',
      type: "'sm' | 'md'",
      defaultValue: "'sm'",
      description: '小标签 / 略大标签。',
    },
    {
      name: 'icon',
      type: 'string | ReactNode',
      defaultValue: 'undefined',
      description: '可选前置图标（Icon 名或节点）。',
    },
    {
      name: 'onDelete',
      type: '() => void',
      defaultValue: 'undefined',
      description: '有则显示关闭按钮。',
    },
    {
      name: 'children / label',
      type: 'ReactNode',
      defaultValue: '—',
      description: '标签文案；children 优先于 label。',
    },
  ],
  scenarios: [
    '未达成：variant="outline" + status（空心）。',
    '已达成 / 已配置：variant="solid" + status="success"（实心）。',
    '分类标签：variant="solid" + color="violet" / cyan（实心）。',
    '可移除筛选条件：onDelete。',
  ],
  antiPatterns: [
    '不要用 Tag 做大段说明（用 Message）。',
    '不要把业务 status→样式映射塞进 Tag（第二层 helper / 页面负责）。',
    '不要同时依赖 status 与 color（有 color 即颜色模式）。',
    '产品里不要用 soft 表示完成态；未完成用 outline，完成与分类标签用 solid。',
  ],
};

export default doc;
