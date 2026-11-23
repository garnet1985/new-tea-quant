import { parseStrategyDesignRoute } from 'containers/strategyDesign';
import { STRATEGY_DESIGN_RUN_STEP_KEYS } from 'containers/strategyDesign/constants/strategyDesignSteps';

const DESIGN_PREFIX = '/strategy-design/';

function parseDesignStep(pathname) {
  const path = String(pathname || '');
  if (!path.startsWith(DESIGN_PREFIX)) return { strategyName: '', step: '' };
  return parseStrategyDesignRoute(path.slice(DESIGN_PREFIX.length));
}

/** 机会盘点 / 价格回测 / 投资模拟（与 STRATEGY_DESIGN_RUN_STEP_KEYS 对齐）。 */
export function matchStrategyDesignWorkbench(pathname) {
  const { strategyName, step } = parseDesignStep(pathname);
  return Boolean(strategyName) && STRATEGY_DESIGN_RUN_STEP_KEYS.has(step);
}

export function matchStrategyDesignEnum(pathname) {
  const { strategyName, step } = parseDesignStep(pathname);
  return Boolean(strategyName) && step === 'enum';
}

export function matchStrategyDesignPrice(pathname) {
  const { strategyName, step } = parseDesignStep(pathname);
  return Boolean(strategyName) && step === 'price';
}

export function matchStrategyDesignPortfolio(pathname) {
  const { strategyName, step } = parseDesignStep(pathname);
  return Boolean(strategyName) && step === 'portfolio';
}

/** 各步骤共用的壳层控件引导（跟在步骤简介后面）。 */
export const STRATEGY_LAYOUT_STEPS = [
  {
    target: 'strategy-intro',
    pages: [
      {
        title: '策略简介',
        body: '这里是策略的基本信息。这些信息来自您本地策略文件夹中 settings.py 的基本信息（meta）。',
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
        title: '策略设置',
        body: '这里是策略设置的快捷入口，它们本质上都来自策略文件夹内的 settings.py。',
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
        title: '全局设置',
        body: '全局设置会作用于所有回测步骤。修改后建议从「机会盘点」重新运行。',
      },
    ],
  },
  {
    target: 'design-settings-specific',
    pages: [
      {
        title: '当前步骤设置',
        body: '这里是当前回测步骤专用的设置；修改后只影响本步。',
      },
    ],
  },
  {
    target: 'design-execution',
    pages: [
      {
        title: '执行面板',
        body: '在这里启动、重跑本步回测，并查看执行进度。',
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
        body: '如果您运行后面的步骤，程序会自动补跑其依赖步骤。',
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
];

/**
 * @deprecated 已拆成 enum/price/portfolio 各一份；保留导出以免旧引用断裂。
 * 新目录请用 STRATEGY_DESIGN_ENUM_HELP 等。
 */
export const STRATEGY_LAYOUT_HELP = {
  id: 'strategy-design',
  version: 1,
  trigger: 'enter',
  match: matchStrategyDesignWorkbench,
  steps: STRATEGY_LAYOUT_STEPS,
};

/**
 * 工作台三步共用同一个 dismiss id：第一次进任一回测步骤弹完整引导，
 * 关掉后换步骤不再整轮重弹（步骤专属文案仍可通过右上角 Help 手动打开）。
 */
const STRATEGY_DESIGN_HELP_ID = 'strategy-design';

/** 机会盘点：无焦点简介 + 共用壳层引导。 */
export const STRATEGY_DESIGN_ENUM_HELP = {
  id: STRATEGY_DESIGN_HELP_ID,
  version: 1,
  trigger: 'enter',
  match: matchStrategyDesignEnum,
  steps: [
    {
      pages: [
        {
          title: '机会盘点',
          body: '本步盘点当前回测股票池里所有可用「机会」，以及它们在历史上的结果，用来看策略发现机会的能力。',
        },
        {
          title: '核心结果看什么',
          body: '报告里重点看机会数量、完整度与分布；「逐股样本」可点开单股核对。跑完后右侧会出现本步回测报告。',
        },
      ],
    },
    ...STRATEGY_LAYOUT_STEPS,
  ],
};

/** 价格回测：无焦点简介 + 共用壳层引导。 */
export const STRATEGY_DESIGN_PRICE_HELP = {
  id: STRATEGY_DESIGN_HELP_ID,
  version: 1,
  trigger: 'enter',
  match: matchStrategyDesignPrice,
  steps: [
    {
      pages: [
        {
          title: '价格回测',
          body: '本步把上一步的「机会」归并后，对每只股票按「投入 1 股」模拟，看这些机会单独拿来做是否盈利。',
        },
        {
          title: '核心结果看什么',
          body: '关注单股盈亏与收益分布，判断机会质量；同样可在「逐股样本」点开明细。',
        },
      ],
    },
    ...STRATEGY_LAYOUT_STEPS,
  ],
};

/** 投资模拟：无焦点简介 + 共用壳层引导。 */
export const STRATEGY_DESIGN_PORTFOLIO_HELP = {
  id: STRATEGY_DESIGN_HELP_ID,
  version: 1,
  trigger: 'enter',
  match: matchStrategyDesignPortfolio,
  steps: [
    {
      pages: [
        {
          title: '投资模拟',
          body: '本步在有「资金上限」的前提下，加入资金分配策略，模拟更接近实盘的组合交易。',
        },
        {
          title: '核心结果看什么',
          body: '重点看总收益率、回撤与资金利用率等账户层指标；「逐笔投资」右上角图表可打开组合事件图。',
        },
      ],
    },
    ...STRATEGY_LAYOUT_STEPS,
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
          body: '若仅改参数，可在这里恢复到某个历史版本的配置。',
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

/**
 * 逐股表在报告数据拉齐后才挂上，且晚于 version 胶囊；单独 appear，避免绑在
 * strategy-version-and-report 里第一次就被跳过。
 */
export const STRATEGY_REPORT_STOCK_HELP = {
  id: 'strategy-report-stock',
  version: 1,
  trigger: 'appear',
  match: matchStrategyDesignWorkbench,
  steps: [
    {
      target: 'strategy-report-stock',
      pages: [
        {
          title: '逐股可点开',
          body: '「逐股样本」里的股票代码可以点击，打开该股的回测明细与图表，方便逐只核对机会与走势。',
        },
      ],
    },
  ],
};

/** 投资模拟报告专属：逐笔事件图入口不易发现。 */
export const STRATEGY_REPORT_PORTFOLIO_CHART_HELP = {
  id: 'strategy-report-portfolio-chart',
  version: 1,
  trigger: 'appear',
  match: matchStrategyDesignPortfolio,
  steps: [
    {
      target: 'strategy-report-portfolio-chart',
      pages: [
        {
          title: '组合可视化',
          body: '「逐笔投资」右上角的图表按钮可打开整表事件图：在净值曲线上查看开仓点分布，方便从组合层审视交易。',
        },
      ],
    },
  ],
};
