/** 图鉴用规范摘要（与 README.md 保持一致，中文）。 */
const doc = {
  summary: '模态对话框。用于确认危险操作或需要用户明确应答的说明；轻量反馈用 Message / Toast。',
  params: [
    {
      name: 'open / onClose',
      type: '受控',
      defaultValue: '—',
      description: '开关与关闭回调（遮罩 / Esc）。忙碌时由调用方在 onClose 内忽略。',
    },
    {
      name: 'title',
      type: 'ReactNode',
      defaultValue: "''",
      description: '标题；空则不渲染标题区。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '正文内容。',
    },
    {
      name: 'actions',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '底部操作区，通常为 Button 组合。',
    },
    {
      name: 'size',
      type: "'sm' | 'md' | 'lg'",
      defaultValue: "'sm'",
      description: '宽度：窄确认 / 说明 / 较宽。',
    },
    {
      name: 'elevated',
      type: 'boolean',
      defaultValue: 'false',
      description: '叠在另一个 Dialog 之上（二次确认）；勿在业务侧用 sx 抬 z-index。',
    },
  ],
  scenarios: [
    '清理缓存 / 重新安装 / 导入数据等确认。',
    '需要阅读后果后再继续的短说明。',
    '已有 Dialog 打开时再弹删除确认：elevated。',
  ],
  antiPatterns: [
    '不要用 Dialog 代替 Toast / Message 做瞬时反馈。',
    '页面禁止直接 import MUI Dialog。',
    '不要在 Dialog 内再嵌一套全页布局。',
    '不要在业务侧用 sx 改 z-index；用 elevated。',
  ],
};

export default doc;
