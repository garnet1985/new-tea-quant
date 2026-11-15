/** 图鉴用规范摘要（与 README.md 保持一致，中文）。 */
const doc = {
  summary: '产品内默认的矩形操作按钮。基于 MUI Button，用 NTQ 视觉变体覆盖样式。',
  params: [
    {
      name: 'variant',
      type: "'glass' | 'primary' | 'attention' | 'ghost'",
      defaultValue: "'glass'",
      description: '视觉变体：玻璃描边 / 主色实心 / 吸睛描边 / 轻量文本。',
    },
    {
      name: 'icon',
      type: 'string',
      defaultValue: "''",
      description: '可选前置图标名，走 NtqIcon 注册表（如 add、settings）。',
    },
    {
      name: 'iconSize',
      type: "'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '前置图标尺寸 token。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '按钮文案。',
    },
    {
      name: '...rest',
      type: 'MUI Button props',
      defaultValue: '—',
      description: '透传给 MUI Button（onClick、disabled、size、type 等）。注意：variant / color / startIcon / className 由本组件接管。',
    },
  ],
  scenarios: [
    '对话框主操作 / 取消：primary + ghost。',
    '列表行内次要操作：glass（可配 size="small"）。',
    '需要短暂吸引注意的入口：attention。',
    '带图标的工具操作：glass/primary + icon。',
  ],
  antiPatterns: [
    '不要在业务页直接用裸 MUI Button 冒充规范按钮。',
    '不要用 rainbowButton 做普通 CRUD；那是强调态 / 品牌态圆形或胶囊按钮。',
    '不要把业务布局逻辑塞进按钮（例如在 onClick 里堆页面跳转编排以外的复杂 UI）。',
    '不要同时传入 MUI 的 variant/color 期望覆盖 NTQ 变体——会被本组件覆盖。',
  ],
};

export default doc;
