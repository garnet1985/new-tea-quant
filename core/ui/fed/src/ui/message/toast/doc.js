const doc = {
  summary: '右下角短暂弹出：应用壳挂载 ToastHost，业务侧调用 showToast({ status, content, duration })。内部复用 Message（状态模式）。',
  params: [
    {
      name: 'showToast.status',
      type: "'success' | 'error' | 'warning' | 'info'",
      defaultValue: "'info'",
      description: '与 Message.status 一致。',
    },
    {
      name: 'showToast.content',
      type: 'ReactNode',
      defaultValue: '—',
      description: '文案；空字符串不弹出。',
    },
    {
      name: 'showToast.duration',
      type: 'number',
      defaultValue: '2800',
      description: '自动关闭毫秒数。',
    },
    {
      name: 'ToastHost',
      type: '组件',
      defaultValue: '—',
      description: '固定右下角宿主；全应用挂一次。',
    },
  ],
  scenarios: [
    '保存成功 / 失败的短暂反馈。',
    '复制到剪贴板等轻量操作结果。',
  ],
  antiPatterns: [
    '不要在每个页面各自再挂 ToastHost。',
    '不要用 Toast 承载需长期阅读的说明（用 Message）。',
    '不要再传 tone / severity；用 status。',
  ],
};

export default doc;
