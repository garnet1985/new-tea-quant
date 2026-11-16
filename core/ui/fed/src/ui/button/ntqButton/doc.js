/** 图鉴用规范摘要（与 README.md 保持一致，中文）。 */
const doc = {
  summary: '产品内默认矩形操作按钮。支持前置/后置图标、纯图标、tooltip；可用 href / component 做成按钮样式的超链接。',
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
      description: '图标名（NtqIcon 注册表）。无 children 时为纯图标按钮。',
    },
    {
      name: 'iconPlacement',
      type: "'start' | 'end'",
      defaultValue: "'start'",
      description: '图标在文案前或后；纯图标时忽略。',
    },
    {
      name: 'iconSize',
      type: "'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '图标尺寸 token。',
    },
    {
      name: 'tooltip',
      type: 'string',
      defaultValue: "''",
      description: '悬停说明；纯图标强烈建议提供（亦可作 aria-label 回退）。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '按钮文案；省略且有 icon 时为纯图标按钮。',
    },
    {
      name: 'href / component / to',
      type: 'MUI Button 链接 props',
      defaultValue: '—',
      description: '做成按钮样式超链接：href 外链，或 component={Link} + to。行内文字链仍用 .ntq-link。',
    },
    {
      name: '...rest',
      type: 'MUI Button props',
      defaultValue: '—',
      description: '透传 onClick、disabled、size、type、aria-label 等。variant/color/startIcon/endIcon/className 由本组件接管。',
    },
  ],
  scenarios: [
    '对话框主操作 / 取消：primary + ghost。',
    '带后置箭头：icon + iconPlacement="end"。',
    '工具栏纯图标：仅 icon + tooltip + aria-label。',
    '按钮样式链接：href 或 RouterLink component。',
  ],
  antiPatterns: [
    '不要在业务页直接用裸 MUI Button。',
    '纯图标按钮禁止省略可访问名称（tooltip 或 aria-label）。',
    '行内文字超链接用 .ntq-link，不要用 NtqButton 冒充正文链。',
    '不要用 rainbowButton 做普通 CRUD。',
  ],
};

export default doc;
