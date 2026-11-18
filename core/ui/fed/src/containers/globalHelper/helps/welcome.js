export function matchWelcome(pathname) {
  return String(pathname || '') === '/welcome';
}

/** 欢迎页：单页说明，不挖洞聚焦任何元素。 */
export const WELCOME_HELP = {
  id: 'welcome',
  version: 1,
  trigger: 'enter',
  match: matchWelcome,
  steps: [
    {
      pages: [
        {
          title: '这里是帮助文档',
          body: '您可以在任何有帮助文档的页面打开我然后获得页面的基本操作帮助。',
        },
      ],
    },
  ],
};
