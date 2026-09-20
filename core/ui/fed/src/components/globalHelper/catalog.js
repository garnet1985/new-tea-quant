import {
  STRATEGY_LAYOUT_HELP,
  STRATEGY_REPORT_COMPARE_HELP,
  STRATEGY_VERSION_AND_REPORT_HELP,
} from './helps/strategyDesign';
import { STRATEGY_DESIGN_DECISION_HELP } from './helps/strategyDesignDecision';

export {
  matchStrategyDesignWorkbench,
  STRATEGY_LAYOUT_HELP,
  STRATEGY_REPORT_COMPARE_HELP,
  STRATEGY_VERSION_AND_REPORT_HELP,
} from './helps/strategyDesign';
export {
  matchStrategyDesignDecision,
  STRATEGY_DESIGN_DECISION_HELP,
} from './helps/strategyDesignDecision';

/** 所有页面的 help。新页面：在 helps/ 加文件，再推进这个数组。 */
export const GLOBAL_HELPER_CATALOG = [
  STRATEGY_LAYOUT_HELP,
  STRATEGY_VERSION_AND_REPORT_HELP,
  STRATEGY_REPORT_COMPARE_HELP,
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
  const ids = [help.id, ...(Array.isArray(help.legacyIds) ? help.legacyIds : [])];
  return ids.some((id) => {
    const row = dismissed[id];
    if (!row) return false;
    return Number(row.version || 0) >= catalogVersion;
  });
}
