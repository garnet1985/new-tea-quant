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
          title: '您好，欢迎使用新茶量化',
          body: '新茶量化是一款针对中国A股的投资量化策略研究平台。它集成了数据获取、策略开发、回测、扫描等功能，通过AI赋能，帮助您轻松研发自己的量化投资策略。',
        },
        {
          title: '在制定策略里',
          body: '您可以制定和验证您的任何想法，当然如果您不擅长代码，AI新茶小助手也可以帮您完成。',
        },
        {
          title: '在策略选股里',
          body: '您可以通过扫描当下市场，选出符合您的策略的投资机会。',
        },
        {
          title: '在高级功能里',
          body: '您还可以体验数据的获取，对比趋势，标记股票等等高级功能。',
        },
        {
          title: '如果您在操作过程中有任何疑问',
          body: '别忘了点击右上角的AI助手随时咨询，新茶小助手一定会尽力帮助您。',
        },
        {
          title: '最后，如果您有任何想法',
          body: '请您不要犹豫随时通过主导航栏的反馈进行匿名反馈。',
        },
      ],
    },
  ],
};
