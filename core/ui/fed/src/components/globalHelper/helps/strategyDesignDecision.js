export function matchStrategyDesignDecision(pathname) {
  const segs = String(pathname || '').split('/').filter(Boolean);
  if (segs[0] !== 'strategy-design' || segs.length < 3) return false;
  const step = decodeURIComponent(segs[segs.length - 1] || '');
  return step === 'decision';
}

/**
 * 决策模拟对局现场。枚举/投资未完成时只有闸门，对局 DOM 还没挂上，
 * 所以用 appear：等执行栏出现再弹。
 */
export const STRATEGY_DESIGN_DECISION_HELP = {
  id: 'strategy-design-decision',
  version: 1,
  trigger: 'appear',
  legacyIds: [],
  match: matchStrategyDesignDecision,
  steps: [
    {
      target: 'decision-exec',
      pages: [
        {
          title: '决策模拟',
          body: '这是回测的最后一步，就是模拟器会让您置身于过去的模拟开始日期的时间点，然后逐步推进日期到模拟结束。',
        },
        {
          title: '推进日期',
          body: '您可以手动推进时间，如果当前策略在当前时间点发现了机会，会马上汇报给您，您需要您在回测的时候注入的数据和已知条件来进行机会的选择。',
        },
        {
          title: '机会的跟进',
          body: '一但您选择了某个机会，这个机会将转交给系统严格按照您的回测的纪律执行。如果完成了某个策略目标，日历会停下向您汇报。',
        },
        {
          title: '总结',
          body: '总而言之，在决策模拟中，您只能选择机会并决定投资的金额，其他的都无法直接干预。当所有模拟完成后，系统将会把您的结果和系统跑的结果进行对比。通过这个模式，您能更直观地感受策略的参数是否合理，压力是不是适合您等等。',
        },
      ],
    },
    {
      target: 'decision-sessions',
      pages: [
        {
          title: '模拟局',
          body: '同一版本的回测可以开多局。「继续」回到未完成的局，「管理」里可以删除旧局，「新开一局」从回测起点重新开始。',
        },
      ],
    },
    {
      target: 'decision-clock',
      pages: [
        {
          title: '当前停顿日',
          body: '这里显示当前模拟停在哪一天，以及已经走了多少个交易日。「事件回溯」可以打开月历，从而直观地看到过去发生的事件。',
        },
      ],
    },
    {
      target: 'decision-advance',
      pages: [
        {
          title: '推进到下一事件',
          body: '点击「下一个事件」或按空格键提交当天。如果当天有可买机会，会先让您确认；什么都不选等于本日不买。提交后当天选择不能再改。',
        },
      ],
    },
    {
      target: 'decision-metrics',
      pages: [
        {
          title: '账户',
          body: '账户价值是现金加持仓市值；可用资金是当天还能用来买股票的钱。推进之后这两项会跟着买卖一起变。',
        },
      ],
    },
    {
      target: 'decision-holdings',
      pages: [
        {
          title: '持仓',
          body: '左侧是当前还拿着的股票。点一行可以看买入价、浮动盈亏和策略目标。卖出由策略规则在推进时自动处理，不在这里手动卖。',
        },
      ],
    },
    {
      target: 'decision-events',
      pages: [
        {
          title: '今日事件',
          body: '刚推进过来的这一天，如果有股票按策略卖出或结算，会列在这里。没有出场时会显示今日无出场结算。',
        },
      ],
    },
    {
      target: 'decision-opps',
      pages: [
        {
          title: '今日机会',
          body: '当天策略发现的可买股票。点股票名称可以看停在当前日的 K 线。可以点「建议买入」填入建议股数，或自己在投资栏改股数。已经持有的标的不能再买。',
        },
      ],
    },
  ],
};
