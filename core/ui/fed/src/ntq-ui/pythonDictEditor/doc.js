const doc = {
  summary: 'NTQ 特有：JSON / Python dict 编辑面板（验证、样例、错误定位）。onChange 接收字符串。不属通用 input。',
  params: [
    {
      name: 'value / onChange',
      type: 'string / (text) => void',
      defaultValue: '—',
      description: '编辑区内容；onChange 直接收字符串（非 e.target）。',
    },
    {
      name: 'onApply / onLoadDefault / onLoadLarge / onConvertPythonLiteral',
      type: '() => void',
      defaultValue: '—',
      description: '工具栏操作；未传则不渲染对应按钮。',
    },
    {
      name: 'parseError / lineHint / errorLine / errorColumn / errorContext',
      type: '错误态',
      defaultValue: '—',
      description: '解析失败信息与上下文行 { lineNo, text, isError }[]。',
    },
    {
      name: 'inputRef',
      type: 'ref',
      defaultValue: '—',
      description: '跳转到错误行时操作 textarea。',
    },
    {
      name: 'title',
      type: 'string',
      defaultValue: "'左栏：Raw JSON 输入'",
      description: '面板标题。',
    },
  ],
  scenarios: [
    'settings.core / 策略参数等 JSON·Python dict 调试与校验。',
  ],
  antiPatterns: [
    '普通多行备注用 TextArea。',
    '不要在业务里再包一层 Paper + MUI Alert 重复壳。',
  ],
};

export default doc;
