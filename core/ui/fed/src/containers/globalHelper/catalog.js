import {
  STRATEGY_DESIGN_ENUM_HELP,
  STRATEGY_DESIGN_PORTFOLIO_HELP,
  STRATEGY_DESIGN_PRICE_HELP,
  STRATEGY_REPORT_COMPARE_HELP,
  STRATEGY_REPORT_PORTFOLIO_CHART_HELP,
  STRATEGY_REPORT_STOCK_HELP,
  STRATEGY_VERSION_AND_REPORT_HELP,
} from './helps/strategyDesign';
import {
  STRATEGY_DESIGN_DECISION_HELP,
  STRATEGY_DESIGN_DECISION_INTRO_HELP,
} from './helps/strategyDesignDecision';
import { DATA_CONTRACT_LIST_HELP } from './helps/dataContractList';
import { DATA_SOURCE_LIST_HELP } from './helps/dataSourceList';
import { SCAN_HELP } from './helps/scan';
import { POST_PROCESS_HELP } from './helps/postProcess';
import { SERIES_RELATION_DETAIL_HELP } from './helps/seriesRelationDetail';
import { SERIES_RELATION_LIST_HELP } from './helps/seriesRelationList';
import { STRATEGY_LIST_HELP } from './helps/strategyList';
import { TAG_LIST_HELP } from './helps/tagList';
import { WELCOME_HELP } from './helps/welcome';

export {
  matchStrategyDesignEnum,
  matchStrategyDesignPortfolio,
  matchStrategyDesignPrice,
  matchStrategyDesignWorkbench,
  STRATEGY_DESIGN_ENUM_HELP,
  STRATEGY_DESIGN_PORTFOLIO_HELP,
  STRATEGY_DESIGN_PRICE_HELP,
  STRATEGY_LAYOUT_HELP,
  STRATEGY_LAYOUT_STEPS,
  STRATEGY_REPORT_COMPARE_HELP,
  STRATEGY_REPORT_PORTFOLIO_CHART_HELP,
  STRATEGY_REPORT_STOCK_HELP,
  STRATEGY_VERSION_AND_REPORT_HELP,
} from './helps/strategyDesign';
export {
  matchStrategyDesignDecision,
  STRATEGY_DESIGN_DECISION_HELP,
  STRATEGY_DESIGN_DECISION_INTRO_HELP,
} from './helps/strategyDesignDecision';
export {
  matchStrategyList,
  STRATEGY_LIST_HELP,
} from './helps/strategyList';
export {
  matchScan,
  SCAN_HELP,
} from './helps/scan';
export {
  matchTagList,
  TAG_LIST_HELP,
} from './helps/tagList';
export {
  matchDataSourceList,
  DATA_SOURCE_LIST_HELP,
} from './helps/dataSourceList';
export {
  matchDataContractList,
  DATA_CONTRACT_LIST_HELP,
} from './helps/dataContractList';
export {
  matchSeriesRelationList,
  SERIES_RELATION_LIST_HELP,
} from './helps/seriesRelationList';
export {
  matchSeriesRelationDetail,
  SERIES_RELATION_DETAIL_HELP,
} from './helps/seriesRelationDetail';
export {
  matchPostProcess,
  POST_PROCESS_HELP,
} from './helps/postProcess';
export {
  matchWelcome,
  WELCOME_HELP,
} from './helps/welcome';

/** 所有页面的 help。新页面：在 helps/ 加文件，再推进这个数组。 */
export const GLOBAL_HELPER_CATALOG = [
  WELCOME_HELP,
  STRATEGY_LIST_HELP,
  SCAN_HELP,
  TAG_LIST_HELP,
  DATA_SOURCE_LIST_HELP,
  DATA_CONTRACT_LIST_HELP,
  SERIES_RELATION_LIST_HELP,
  SERIES_RELATION_DETAIL_HELP,
  POST_PROCESS_HELP,
  STRATEGY_DESIGN_ENUM_HELP,
  STRATEGY_DESIGN_PRICE_HELP,
  STRATEGY_DESIGN_PORTFOLIO_HELP,
  STRATEGY_DESIGN_DECISION_INTRO_HELP,
  STRATEGY_VERSION_AND_REPORT_HELP,
  STRATEGY_REPORT_STOCK_HELP,
  STRATEGY_REPORT_COMPARE_HELP,
  STRATEGY_REPORT_PORTFOLIO_CHART_HELP,
  STRATEGY_DESIGN_DECISION_HELP,
];

export function helpTrigger(help) {
  return help?.trigger === 'appear' ? 'appear' : 'enter';
}

export function findHelpsForPath(pathname) {
  return GLOBAL_HELPER_CATALOG.filter((help) => (
    help && typeof help.match === 'function' && help.match(pathname)
  ));
}

export function findHelpForPath(pathname) {
  return findHelpsForPath(pathname)[0] || null;
}

export function pickHelpForManualOpen(helps) {
  const list = Array.isArray(helps) ? helps : [];
  const enter = list.find((item) => helpTrigger(item) === 'enter');
  return enter || list[0] || null;
}

export function isHelpDismissed(help, dismissed = {}) {
  if (!help) return false;
  const catalogVersion = Number(help.version) > 0 ? Number(help.version) : 1;
  const row = dismissed[help.id];
  if (!row) return false;
  return Number(row.version || 0) >= catalogVersion;
}
