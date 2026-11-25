const doc = {
  summary: '消息条。inline=圆角+border+底色（无 bar）；banner=左侧 bar、无圆角。状态模式图标固定；颜色模式可传/省略 icon。',
  params: [
    {
      name: 'status',
      type: "'success' | 'error' | 'warning' | 'info'",
      defaultValue: "'info'",
      description: '语义状态（绿/红/黄/青）。图标固定，忽略 icon。与 color 二选一；传了 color 则走颜色模式。',
    },
    {
      name: 'color',
      type: "'green' | 'error' | 'warning' | 'muted' | 'cyan' | 'violet'",
      defaultValue: 'undefined',
      description: '纯颜色模式（含紫）。有 color 时不用 status；icon 可传入或省略。',
    },
    {
      name: 'variant',
      type: "'inline' | 'banner'",
      defaultValue: "'inline'",
      description: 'inline=圆角无 bar；banner=有 bar 且无圆角（header 下通栏）。',
    },
    {
      name: 'icon',
      type: "string | ReactNode | false",
      defaultValue: '颜色模式省略；状态模式固定',
      description: '仅颜色模式生效：图标名或节点；省略则无图标。状态模式下不可改。',
    },
    {
      name: 'onClose',
      type: '() => void',
      defaultValue: 'undefined',
      description: '有则显示关闭按钮。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '消息正文。',
    },
  ],
  scenarios: [
    '操作结果：status="success" | "error"。',
    '页面说明条：status="info" variant="banner"。',
    '装饰性说明：color="violet" / color="muted"，可选 icon。',
  ],
  antiPatterns: [
    '不要用 Message 做右下角短暂弹出（用 Toast / showToast）。',
    '不要在状态模式下指望改 icon（会被忽略）。',
    '不要同时依赖 status 与 color（有 color 即颜色模式）。',
  ],
};

export default doc;
