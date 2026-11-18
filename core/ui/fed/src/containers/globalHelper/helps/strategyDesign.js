import { parseStrategyDesignRoute } from 'containers/strategyDesign';
import { STRATEGY_DESIGN_RUN_STEP_KEYS } from 'containers/strategyDesign/constants/strategyDesignSteps';

const DESIGN_PREFIX = '/strategy-design/';

/** 机会盘点 / 价格回测 / 投资模拟（与 STRATEGY_DESIGN_RUN_STEP_KEYS 对齐）。 */
export function matchStrategyDesignWorkbench(pathname) {
  const path = String(pathname || '');
  if (!path.startsWith(DESIGN_PREFIX)) return false;
  const { strategyName, step } = parseStrategyDesignRoute(path.slice(DESIGN_PREFIX.length));
  return Boolean(strategyName) && STRATEGY_DESIGN_RUN_STEP_KEYS.has(step);
}

/** 制定策略内页：进页即可看到的栏位。 */
export const STRATEGY_LAYOUT_HELP = {
  id: 'strategy-design',
  version: 1,
  trigger: 'enter',
  match: matchStrategyDesignWorkbench,
  steps: [
    {
      target: 'strategy-intro',
      pages: [
        {
          title: '策略简介',
          body: '这里是策略的基本信息栏位。这些信息来自您本地策略文件夹中的settings.py文件的meta信息块。',
        },
      ],
    },
    {
      target: 'strategy-actions',
      pages: [
        {
          title: '策略操作',
          body: '这里可以对策略进行快捷操作。',
        },
      ],
    },
    {
      target: 'strategy-open',
      pages: [
        {
          title: '打开策略文件夹',
          body: '这里可以打开策略的文件夹位置，方便您修改代码和设置。',
        },
      ],
    },
    {
      target: 'strategy-export',
      pages: [
        {
          title: '导出策略',
          body: '这里可以导出策略的代码和设置变成单独的zip包，然后在策略选择页面可以直接导入，方便分享和转移您的策略。',
        },
      ],
    },
    {
      target: 'design-settings',
      pages: [
        {
          title: '策略设置栏',
          body: '这里是策略的一部分设置调整的快捷入口，他们本质上都来源于您策略文件夹内的settings.py文件。',
        },
        {
          title: '当设置发生变动',
          body: '当您的策略设置发生任何变动之后，您运行的结果将变成基于改动后设置的一个新的版本。',
        },
      ],
    },
    {
      target: 'design-settings-global',
      pages: [
        {
          title: '全局设置栏',
          body: '全局设置是跨回测步骤的设置。当您在回测设置中修改了这些值，它们会作用于所有回测步骤。',
        },
      ],
    },
    {
      target: 'design-settings-specific',
      pages: [
        {
          title: '特定设置栏',
          body: '特定设置是针对当前回测步骤的设置。当您在回测设置中修改了这些值，它们会作用于当前回测步骤。',
        },
      ],
    },
    {
      target: 'design-execution',
      pages: [
        {
          title: '执行栏',
          body: '这里是回测执行的容器，所有对回测的操作可以在这里执行。',
        },
      ],
    },
    {
      target: 'strategy-steps',
      pages: [
        {
          title: '回测步骤',
          body: '这里是回测步骤的快捷入口，您可以通过点击在任意步骤间切换。',
        },
        {
          title: '步骤依赖',
          body: '如果您开始运行后边的步骤，那么程序会自动解析依赖并且自动运行依赖的步骤。',
        },
      ],
    },
    {
      target: 'start-simulation',
      pages: [
        {
          title: '开始模拟',
          body: '您可以试着点击这里开始运行当前的回测步骤了。',
        },
      ],
    },
  ],
};

/**
 * 第一次跑出 version 之后才出现的栏位。
 * 锚点必须打在「动作之后才挂上」的 DOM 上，不能打在进页就在的空壳上。
 */
export const STRATEGY_VERSION_AND_REPORT_HELP = {
  id: 'strategy-version-and-report',
  version: 1,
  trigger: 'appear',
  match: matchStrategyDesignWorkbench,
  steps: [
    {
      target: 'strategy-version',
      pages: [
        {
          title: '回测版本',
          body: '您的不同版本将对应策略的不同配置。之后产生的不同版本将有两种情况，如果只是配置发生变化，您仍然可以回到老版本。但如果是系统代码或环境发生变化导致的新版本，老版本将只能查看结果不可修改或回溯。',
        },
      ],
    },
    {
      target: 'strategy-history',
      pages: [
        {
          title: '回测版本历史',
          body: '您可以在这里轻松回到一个版本历史。（如果只是改参数）',
        },
        {
          title: '回测版本清理',
          body: '过时环境最多留几组，超出则整组删除。当前环境不限份数。系统会标注即将被清理的过时环境。',
        },
      ],
    },
    {
      target: 'strategy-report',
      pages: [
        {
          title: '回测报告',
          body: '您当前回测步骤的报告会出现在这里。请注意每个报告名称后方的 ？图标，会给出当前报告的详细说明。',
        },
      ],
    },
  ],
};

/**
 * 「对比结果」要至少两个版本才出现，不能和第一份 snapshot 的 appear 绑在一起，
 * 否则第一次引导时这一步会被跳过，ack 之后再也不会弹。
 */
export const STRATEGY_REPORT_COMPARE_HELP = {
  id: 'strategy-report-compare',
  version: 1,
  trigger: 'appear',
  match: matchStrategyDesignWorkbench,
  steps: [
    {
      target: 'strategy-report-compare',
      pages: [
        {
          title: '报告对比',
          body: '您可以点击这里对比不同回测版本间的报告方便您清晰看到参数变化所带来的结果变化。',
        },
      ],
    },
  ],
};
