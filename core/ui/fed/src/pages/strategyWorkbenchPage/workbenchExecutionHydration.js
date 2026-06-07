/**
 * 将 V2-01 ``GET …/version/latest`` 的 ``step_status`` / ``result_report`` 转为执行面板用的卡片状态与摘要行。
 */
import { normalizePriceMetricsFromSummary } from './reportMetrics/strategyReportMetricsNormalize';

const IDLE = { enum: 'idle', price: 'idle', capital: 'idle' };

function slotDone(entry) {
  if (!entry || typeof entry !== 'object') return false;
  return entry.done === true;
}

/**
 * @param {object|null|undefined} apiStepStatus BFF：``enum`` / ``price_factor`` / ``capital_allocation`` → ``{ done: boolean }``
 * @returns {{ enum: string, price: string, capital: string }}
 */
export function mapWorkbenchStepStatusToExecutionCards(apiStepStatus) {
  if (!apiStepStatus || typeof apiStepStatus !== 'object') {
    return { ...IDLE };
  }
  return {
    enum: slotDone(apiStepStatus.enum) ? 'done' : 'idle',
    price: slotDone(apiStepStatus.price_factor) ? 'done' : 'idle',
    capital: slotDone(apiStepStatus.capital_allocation) ? 'done' : 'idle',
  };
}

/**
 * 从快照 ``result_report`` 提取执行面板一行摘要（与 progress 切片字段对齐）。
 * @param {object|null|undefined} resultReport
 * @returns {{ enum: object|null, price: object|null, capital: object|null }}
 */
export function buildExecutionResultFromWorkbenchReport(resultReport) {
  const empty = { enum: null, price: null, capital: null };
  if (!resultReport || typeof resultReport !== 'object') {
    return empty;
  }
  const out = { ...empty };

  const enumSlot = resultReport.enum;
  if (enumSlot && typeof enumSlot === 'object') {
    const em = enumSlot.enumMetrics;
    const opp = enumSlot.opportunities
      ?? enumSlot.total_opportunities
      ?? (em && typeof em === 'object' ? em.totalOpportunities : undefined);
    if (opp !== undefined && opp !== null) {
      const n = Number(opp);
      if (Number.isFinite(n)) {
        out.enum = { opportunities: n };
      }
    }
  }

  const pf = resultReport.price_factor;
  if (pf && typeof pf === 'object') {
    const pm = normalizePriceMetricsFromSummary(pf);
    if (pm && Number.isFinite(pm.winRate) && Number.isFinite(pm.avgRoi)) {
      out.price = {
        winRate: pm.winRate,
        roi: pm.avgRoi,
      };
    }
  }

  const cap = resultReport.capital_allocation;
  if (cap && typeof cap === 'object') {
    const profit = Number(cap.total_profit);
    const ic = Number(cap.initial_capital);
    const ec = Number(cap.final_total_equity);
    const tr = Number(cap.total_return);
    const retPct = Number.isFinite(tr) ? tr * 100 : NaN;
    if ([profit, ic, ec, retPct].every((x) => Number.isFinite(x))) {
      out.capital = {
        profit,
        retPct,
        initialCapital: ic,
        endCapital: ec,
      };
    }
  }

  return out;
}
