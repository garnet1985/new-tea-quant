const doc = {
  summary: '顶栏版本号纯展示。字符串由应用层传入，不内置 fetch。',
  params: [
    {
      name: 'label',
      type: 'string',
      defaultValue: '—',
      description: '版本文案；空则不渲染。',
    },
  ],
  scenarios: [
    'AppBrand version 槽：<AppBrand version={<AppVersionMark label={…} />} />。',
  ],
  antiPatterns: [
    '不要在本组件里请求版本 API（用 containers/appVersion）。',
  ],
};

export default doc;
