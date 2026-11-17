/** 图鉴用规范摘要（与 README.md 保持一致，中文）。 */
const doc = {
  summary: '品牌强调按钮：彩虹描边 / 色带图标。用于「运行」「助手」「帮助」等少数高曝光入口，不是通用 CRUD 按钮。',
  params: [
    {
      name: 'shape',
      type: "'circle' | 'pill'",
      defaultValue: "'circle'",
      description: '外形：圆形图标钮 / 圆角胶囊（可带文案）。',
    },
    {
      name: 'size',
      type: "'sm' | 'lg'",
      defaultValue: "'sm'",
      description: '圆形尺寸；胶囊主要靠自身 min-height。',
    },
    {
      name: 'ring',
      type: "'spin' | 'still' | 'plain'",
      defaultValue: "'spin'",
      description: '描边：色带旋转 / 静止渐变 / 灰边无彩虹。',
    },
    {
      name: 'glow',
      type: 'boolean',
      defaultValue: 'false',
      description: '外圈光晕（助手等浮层入口常用）。',
    },
    {
      name: 'quiet',
      type: 'boolean',
      defaultValue: 'false',
      description: '压暗光晕（例如对话面板已打开时）。',
    },
    {
      name: 'shimmer',
      type: 'boolean',
      defaultValue: 'false',
      description: '胶囊文案上的色带流动。',
    },
    {
      name: 'icon',
      type: "'play' | 'refresh' | 'cancel' | ''",
      defaultValue: "''",
      description: 'play/refresh 用色带裁进图标；cancel 走 NtqIcon。',
    },
    {
      name: 'mark',
      type: "'help' | 'ai' | ''",
      defaultValue: "''",
      description: '特殊字标：问号帮助 / AI 角标。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '胶囊文案；圆形通常不用。',
    },
    {
      name: '...rest',
      type: 'button HTML attrs',
      defaultValue: '—',
      description: '透传原生 button（onClick、disabled、aria-label 等）。',
    },
  ],
  scenarios: [
    '策略 / Tag / 数据源「运行」：circle + icon="play"。',
    '全局助手入口：circle + mark="ai" + glow。',
    '帮助入口：circle + mark="help"。',
    '强调主 CTA 胶囊：shape="pill" + ring="spin" + 文案（可 shimmer）。',
    '取消 / 次要同排：pill + ring="plain"。',
  ],
  antiPatterns: [
    '不要用它替代 ntqButton 做编辑、保存、删除等常规操作。',
    '同一屏不要堆很多彩虹钮，会稀释强调效果。',
    '圆形按钮务必提供 aria-label（仅图标时）。',
    '不要在业务里复制彩虹 SCSS；统一从本组件引用。',
  ],
};

export default doc;
