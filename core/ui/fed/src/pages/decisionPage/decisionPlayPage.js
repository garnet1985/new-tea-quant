import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Snackbar,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import PageLayout from '../../components/pageLayout/pageLayout';
import ChartPanel from '../../components/chartPanel/chartPanel';
import InlineLoadingState from '../../components/inlineLoadingState/inlineLoadingState';
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import { buildStockKlineChartOptionFromPayload } from '../strategyWorkbenchPage/panels/strategyReportPanel/lib/stockKlineChart';
import {
  doneDecisionDay,
    fetchDecisionHoldings,
    fetchDecisionInfo,
    fetchDecisionSession,
    holdingsMarketValue,
    nextDecisionDay,
    pickDecisionShares,
    resetDecisionDraft,
} from '../../api/decisionApi';
import { getStrategyDesignPath } from '../../api/strategyApi';
import { isHttpStatusError } from 'services/request';
import {
  buildMonthCells,
  calendarActionLabel,
  calendarActionDetail,
  canShiftMonth,
  countTradingDaysInclusive,
  dateToYearMonth,
  formatMoney,
  formatPct,
  formatSignedMoney,
  indexCalendarDays,
  listOpenDaysAfter,
  mapStockStatusTags,
  monthTitle,
  shiftMonth,
  weekdayLabel,
} from './decisionFormat';
import './decisionPage.scss';

const WEEKDAY_HEADS = ['一', '二', '三', '四', '五', '六', '日'];
const CLOCK_STEP_MS = 300;
const CLOCK_FADE_OUT_MS = 100;

function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function formatDrawdown(value) {
  if (value == null || !Number.isFinite(Number(value))) return '至今无回撤';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function errorMessage(err, fallback) {
  if (isHttpStatusError(err) && err.message) return err.message;
  return String(err?.message || fallback);
}

function formatHoldingPnl(unrealized, pnlPct) {
  if (unrealized == null || !Number.isFinite(Number(unrealized))) return '—';
  const money = formatSignedMoney(unrealized);
  if (pnlPct == null || !Number.isFinite(Number(pnlPct))) return money;
  const n = Number(pnlPct) * 100;
  const sign = n > 0 ? '+' : '';
  return `${money}（${sign}${n.toFixed(1)}%）`;
}

function formatHoldingListPnl(unrealized) {
  if (unrealized == null || !Number.isFinite(Number(unrealized))) return '—';
  const n = Number(unrealized);
  if (n >= 0) return `+${formatMoney(n)}`;
  return formatMoney(n);
}

function holdingPnlTone(unrealized) {
  return Number(unrealized) < 0 ? 'is-loss' : 'is-profit';
}

function formatMarketValueWithPnl(marketValue, unrealized) {
  if (marketValue == null || !Number.isFinite(Number(marketValue))) return '—';
  const value = formatMoney(marketValue);
  if (unrealized == null || !Number.isFinite(Number(unrealized))) return value;
  return (
    <>
      {value}
      {' '}
      <span className={`decision-pnl ${holdingPnlTone(unrealized)}`}>
        ({formatSignedMoney(unrealized)})
      </span>
    </>
  );
}

function StockStatusChips({ tags }) {
  const items = mapStockStatusTags(tags);
  if (!items.length) return null;
  return (
    <span className="decision-status-chips">
      {items.map((item) => (
        <Chip
          key={item.tag}
          size="small"
          variant="outlined"
          label={item.label}
          className={`decision-status-chip is-${item.tag === 'star_st' ? 'star-st' : item.tag}`}
        />
      ))}
    </span>
  );
}

function holdingStockLabel(row) {
  const name = String(row?.name || '').trim();
  const ticker = String(row?.ticker || '').trim();
  if (name && ticker) return `${name}  ${ticker}`;
  return name || ticker || '—';
}

function opportunityStockLabel(row) {
  const name = String(row?.name || '').trim();
  const ticker = String(row?.ticker || '').trim();
  if (name && ticker) return `${name}（${ticker}）`;
  return name || ticker || '—';
}

function inferAShareLot(ticker) {
  // 与 china_a_stock 手数表对齐：现场 lot_step 未到时也能步进。
  const id = String(ticker || '').split('.')[0];
  if (/^688/.test(id)) return { minLot: 200, lotStep: 1 };
  if (/^(8|43|92)/.test(id)) return { minLot: 100, lotStep: 1 };
  return { minLot: 100, lotStep: 100 };
}

function lotRule(row) {
  const inferred = inferAShareLot(row?.ticker);
  const minLot = Number(row?.lotSize) > 0 ? Number(row.lotSize) : inferred.minLot;
  const lotStep = Number(row?.lotStep) > 0 ? Number(row.lotStep) : inferred.lotStep;
  return { minLot, lotStep };
}

function shareStepJump(lotStep) {
  const step = Math.max(1, Number(lotStep) || 1);
  return step >= 100 ? step : 100;
}

function stepShares(current, direction, minLot, lotStep) {
  const min = Math.max(1, Number(minLot) || 1);
  const jump = shareStepJump(lotStep);
  const n = Math.max(0, Math.trunc(Number(current) || 0));
  if (direction > 0) {
    if (n < min) return min;
    return n + jump;
  }
  if (n <= min) return 0;
  const next = n - jump;
  return next < min ? min : next;
}

function validateShareDraft(raw, minLot, lotStep) {
  const text = String(raw ?? '').trim();
  if (!text) return { ok: true, shares: 0 };
  if (!/^\d+$/.test(text)) return { ok: false, message: '股数须为整数' };
  const shares = Number(text);
  if (!Number.isInteger(shares) || shares < 0) return { ok: false, message: '股数须为整数' };
  if (shares === 0) return { ok: true, shares: 0 };
  const min = Math.max(1, Number(minLot) || 1);
  const step = Math.max(1, Number(lotStep) || min);
  if (shares < min) return { ok: false, message: `最少 ${min} 股` };
  if ((shares - min) % step !== 0) {
    return { ok: false, message: `须为 ${min} 起、每 ${step} 股` };
  }
  return { ok: true, shares };
}

function cashFromShares(shares, price) {
  const n = Number(shares) || 0;
  const px = Number(price) || 0;
  if (n <= 0 || px <= 0) return 0;
  return n * px;
}

function headerWithTooltip(label, title) {
  return () => (
    <Tooltip title={title}>
      <span className="decision-col-help">{label}</span>
    </Tooltip>
  );
}

function suggestedBuyTooltip(mode) {
  if (mode === 'equal_shares') {
    return '点按填入建议股数。等股：每次买入手数 × 最小交易单位。';
  }
  if (mode === 'kelly') {
    return '点按填入建议股数。凯莉：当前现金 × 该标的 as-of 胜率 × 凯莉折扣。无已完成样本为 —。';
  }
  return '点按填入建议股数。等价资金：初始资金 ÷ 最大持股数，再按手数折股。';
}

function SuggestedSharesCell({ suggestedCash, suggestedShares, basis, held, disabled, onApply }) {
  if (held) return '—';
  const hasCash = suggestedCash != null && suggestedCash > 0;
  const hasShares = suggestedShares != null && suggestedShares > 0;
  const basisEl = basis ? <span className="decision-suggest-basis">{basis}</span> : null;
  const body = (
    <span className="decision-suggest-cell">
      {hasShares ? `${Number(suggestedShares).toLocaleString()} 股` : '—'}
      {hasShares && hasCash ? (
        <span className="decision-suggest-shares">约 {Number(suggestedCash).toLocaleString()} 元</span>
      ) : null}
      {basisEl}
    </span>
  );
  if (!hasShares) {
    return (
      <span className="decision-suggest-cell">
        —
        {basisEl}
      </span>
    );
  }
  if (disabled) return body;
  return (
    <Button
      size="small"
      variant="text"
      className="decision-suggest-apply"
      onClick={(event) => {
        event.stopPropagation();
        onApply();
      }}
    >
      {body}
    </Button>
  );
}

function SharesInvestCell({
  disabled,
  draft,
  error,
  notional,
  ticker,
  lotStep,
  onDraftChange,
  onCommit,
  onCancel,
  onStep,
}) {
  const jump = shareStepJump(lotStep);
  const stopRow = (event) => event.stopPropagation();
  return (
    <span className="decision-invest-cell" onClick={stopRow} onMouseDown={stopRow}>
      <span className="decision-invest-row">
        <span className={`decision-shares-capsule${error ? ' is-error' : ''}${disabled ? ' is-disabled' : ''}`}>
          <button
            type="button"
            className="decision-capsule-btn"
            disabled={disabled}
            aria-label={`减少 ${jump} 股`}
            onClick={(event) => {
              event.stopPropagation();
              onStep(-1);
            }}
            onMouseDown={(event) => {
              event.preventDefault();
              event.stopPropagation();
            }}
          >
            −
          </button>
          <input
            className="decision-capsule-input"
            type="text"
            inputMode="numeric"
            disabled={disabled}
            value={draft}
            placeholder="股数"
            aria-label={`投资股数 ${ticker}`}
            onClick={stopRow}
            onMouseDown={stopRow}
            onChange={(event) => onDraftChange(event.target.value)}
            onBlur={(event) => onCommit(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'ArrowUp') {
                event.preventDefault();
                onStep(1);
              }
              if (event.key === 'ArrowDown') {
                event.preventDefault();
                onStep(-1);
              }
              if (event.key === 'Enter') {
                event.preventDefault();
                onCommit(event.target.value);
              }
              if (event.key === 'Escape') {
                event.preventDefault();
                onCancel();
              }
            }}
          />
          <button
            type="button"
            className="decision-capsule-btn"
            disabled={disabled}
            aria-label={`增加 ${jump} 股`}
            onClick={(event) => {
              event.stopPropagation();
              onStep(1);
            }}
            onMouseDown={(event) => {
              event.preventDefault();
              event.stopPropagation();
            }}
          >
            +
          </button>
        </span>
        <span className="decision-invest-notional">
          {notional ? `约 ${notional}` : '\u00a0'}
        </span>
      </span>
      {error ? (
        <span className="decision-invest-hint is-error">{error}</span>
      ) : null}
    </span>
  );
}

function formatHoldSpan(days, unit) {
  const n = Number(days) || 0;
  if (unit === 'trading_day') return `${n} 个交易日`;
  if (unit === 'open_day') return `${n} 个开市日`;
  return `${n} 个自然日`;
}

function HoldingDetailDialog({ row, open, equity, onClose, onOpenKline }) {
  const weight = row?.marketValue != null
    && Number.isFinite(Number(row.marketValue))
    && Number.isFinite(Number(equity))
    && Number(equity) > 0
    ? Number(row.marketValue) / Number(equity)
    : null;
  const kv = row ? [
    ['股票', (
      <span className="decision-stock-with-status">
        {holdingStockLabel(row)}
        <StockStatusChips tags={row.statusTags} />
      </span>
    )],
    ['持有', `${Number(row.shares).toLocaleString()} 股`],
    ['买入日', row.buyDate || '—'],
    ['买入价', row.buyPrice != null ? formatMoney(row.buyPrice) : '—'],
    ['现价', row.close != null ? formatMoney(row.close) : '—'],
    ['总成本', row.cost != null ? formatMoney(row.cost) : '—'],
    ['总价值', formatMarketValueWithPnl(row.marketValue, row.unrealized)],
    ['浮动盈亏', formatHoldingPnl(row.unrealized, row.pnlPct)],
    ['持有时长', formatHoldSpan(row.holdDays, row.holdUnit)],
    ['仓位占比', weight == null ? '—' : `${(weight * 100).toFixed(1)}%`],
  ] : [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>持仓明细</DialogTitle>
      <DialogContent dividers>
        {kv.map(([label, value]) => (
          <Typography key={label} className="decision-kv" variant="body2">
            <span className="decision-kv__label">{label}</span>
            <span className="decision-kv__value">{value}</span>
          </Typography>
        ))}
        <Typography variant="subtitle2" sx={{ mt: 2, mb: 0.5 }} fontWeight={700}>
          目标
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
          已按某档卖出的会标已完成；剩下的股仍按当前浮动盈亏显示，不会因为还在列表里就把该档当成没做过。
        </Typography>
        {row?.goals?.length ? (
          <Box className="decision-goal-list">
            {row.goals.map((goal, index) => (
              <Box key={`${goal.kind}-${index}`} className="decision-goal-row">
                <Typography variant="body2" className="decision-goal-row__text">
                  {goal.text}
                </Typography>
                <Chip
                  size="small"
                  variant="outlined"
                  color={goal.done ? 'success' : 'warning'}
                  label={goal.done ? '已完成' : '未完成'}
                />
              </Box>
            ))}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">本策略未配置持仓目标</Typography>
        )}
      </DialogContent>
      <DialogActions>
        {onOpenKline ? <Button onClick={onOpenKline}>查看 K 线</Button> : null}
        <Button variant="contained" onClick={onClose}>关闭</Button>
      </DialogActions>
    </Dialog>
  );
}

function CalendarEventChip({ className, label, detail }) {
  return (
    <Tooltip
      title={<span className="decision-cal-tip">{detail || label}</span>}
      placement="top"
      enterDelay={120}
      enterNextDelay={60}
      describeChild
      slotProps={{
        popper: { sx: { zIndex: 1600 } },
        tooltip: {
          sx: {
            maxWidth: 360,
            fontSize: 12,
            lineHeight: 1.45,
            whiteSpace: 'pre-wrap',
          },
        },
      }}
    >
      <span className={`decision-cal-event ${className || ''}`.trim()}>{label}</span>
    </Tooltip>
  );
}

function MonthGrid({ year, month, clockDate, days, rangeStart, rangeEnd }) {
  const cells = buildMonthCells(year, month);
  return (
    <Box className="decision-month-grid" role="grid" aria-label={`${monthTitle(year, month)} 交易日历`}>
      {WEEKDAY_HEADS.map((label) => (
        <Typography key={label} className="decision-month-head" component="div">
          {label}
        </Typography>
      ))}
      {cells.map((date, index) => {
        if (!date) {
          return <Box key={`empty-${index}`} className="decision-month-cell is-pad" />;
        }
        const outOfRange = (rangeStart && date < rangeStart) || (rangeEnd && date > rangeEnd);
        const future = date > clockDate;
        const day = !outOfRange && !future ? days[date] : null;
        const oppCount = Number(day?.oppCount) || 0;
        const actions = Array.isArray(day?.actions) ? day.actions : [];
        const hasEvents = oppCount > 0 || actions.length > 0;
        return (
          <Box
            key={date}
            className={[
              'decision-month-cell',
              date === clockDate ? 'is-now' : '',
              outOfRange ? 'is-out' : '',
              future ? 'is-future' : '',
              hasEvents ? 'has-events' : '',
            ].filter(Boolean).join(' ')}
          >
            <span className="decision-month-cell__num">{Number(date.slice(8))}</span>
            <span className="decision-month-cell__events">
              {oppCount > 0 ? (
                <CalendarEventChip
                  className="is-opp"
                  label={`发现${oppCount}个机会`}
                />
              ) : null}
              {actions.map((action, actionIndex) => (
                <CalendarEventChip
                  key={`${action.side}-${action.ticker}-${actionIndex}`}
                  className={`is-${action.side}`}
                  label={calendarActionLabel(action)}
                  detail={calendarActionDetail(action)}
                />
              ))}
            </span>
          </Box>
        );
      })}
    </Box>
  );
}

export function DecisionPlaySession({
  strategyKey: strategyKeyProp,
  sessionId: sessionIdProp,
  readonly: readonlyProp,
  hideStrategyMeta = false,
  onViewReport = null,
  onCompleted = null,
  render = null,
} = {}) {
  const [params] = useSearchParams();
  const strategyKey = String(strategyKeyProp || params.get('strategy') || '').trim();
  const readonlyQuery = readonlyProp != null ? Boolean(readonlyProp) : params.get('readonly') === '1';
  const sessionId = String(sessionIdProp || params.get('session') || '').trim();
  const embedded = typeof render === 'function';

  const [snapshot, setSnapshot] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [picks, setPicks] = useState({});
  const [events, setEvents] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [pageReady, setPageReady] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [holdingDetailId, setHoldingDetailId] = useState(null);
  const [infoOpp, setInfoOpp] = useState(null);
  const [infoPayload, setInfoPayload] = useState(null);
  const [infoLoading, setInfoLoading] = useState(false);
  const [shareEditors, setShareEditors] = useState({});
  const [positionOpen, setPositionOpen] = useState(false);
  const [toast, setToast] = useState('');
  const [advancing, setAdvancing] = useState(false);
  const [displayClockDate, setDisplayClockDate] = useState('');
  const [clockMotion, setClockMotion] = useState('is-landed');
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [viewYear, setViewYear] = useState(() => dateToYearMonth('').year);
  const [viewMonth, setViewMonth] = useState(() => dateToYearMonth('').month);
  const animRef = useRef({ cancelled: false, timer: null });
  const pickTimerRef = useRef(null);
  const pendingPicksRef = useRef({});
  const runAdvanceRef = useRef(null);
  const spaceLockRef = useRef(false);
  const holdingDetailCacheRef = useRef(null);
  const designHref = strategyKey
    ? getStrategyDesignPath(strategyKey, 'decision')
    : '/strategy-design';

  const applyLive = useCallback((snap, nextHoldings, { hopEvents, keepPicks = false } = {}) => {
    setSnapshot(snap);
    if (Array.isArray(nextHoldings)) setHoldings(nextHoldings);
    if (!keepPicks) {
      setPicks(snap.picks || {});
      setShareEditors({});
    }
    if (hopEvents !== undefined) setEvents(hopEvents);
    const month = dateToYearMonth(snap.clockDate);
    if (snap.clockDate) {
      setViewYear(month.year);
      setViewMonth(month.month);
    }
  }, []);

  const loadHoldings = useCallback(async (dmId) => {
    if (!strategyKey || !dmId) return [];
    try {
      return await fetchDecisionHoldings(strategyKey, dmId);
    } catch {
      return [];
    }
  }, [strategyKey]);

  useEffect(() => {
    const anim = animRef.current;
    anim.cancelled = false;
    if (!strategyKey || !sessionId) {
      if (!embedded) {
        setLoadError('缺少策略或对局');
        setPageReady(true);
      }
      return undefined;
    }

    let cancelled = false;
    (async () => {
      setPageReady(false);
      setLoadError('');
      setEvents([]);
      try {
        const snap = await fetchDecisionSession(strategyKey, sessionId);
        if (cancelled) return;
        const held = await loadHoldings(snap.dmId);
        if (cancelled) return;
        applyLive(snap, held, { hopEvents: [], keepPicks: false });
      } catch (err) {
        if (!cancelled) setLoadError(errorMessage(err, '无法打开对局'));
      } finally {
        if (!cancelled) setPageReady(true);
      }
    })();

    return () => {
      cancelled = true;
      anim.cancelled = true;
      if (anim.timer) window.clearTimeout(anim.timer);
      if (pickTimerRef.current) window.clearTimeout(pickTimerRef.current);
    };
  }, [strategyKey, sessionId, embedded, applyLive, loadHoldings]);

  const clockDate = snapshot?.clockDate || '';
  const shownClockDate = displayClockDate || clockDate;
  const completed = Boolean(snapshot?.completed || readonlyQuery);
  const completedNoticeKey = `${strategyKey}:${sessionId}`;
  const completedNoticeRef = useRef('');
  useEffect(() => {
    if (!completed || typeof onCompleted !== 'function') return undefined;
    if (completedNoticeRef.current === completedNoticeKey) return undefined;
    completedNoticeRef.current = completedNoticeKey;
    onCompleted();
    return undefined;
  }, [completed, completedNoticeKey, onCompleted]);
  const rangeStart = snapshot?.startDate || '';
  const rangeEnd = snapshot?.endDate || '';
  const holdingsValue = holdingsMarketValue(holdings);
  const equity = (Number(snapshot?.cash) || 0) + holdingsValue;
  const initialCash = Number(snapshot?.initialCash) || 0;
  const equityDelta = initialCash > 0 ? equity - initialCash : null;
  const cashRatio = equity > 0 ? (Number(snapshot?.cash) || 0) / equity : null;
  const hasOpps = Boolean(snapshot?.hasOpps);
  const maxPortfolioSize = Number(snapshot?.maxPortfolioSize) || 0;
  const openPositionCount = Number(snapshot?.openPositionCount) || 0;
  const activePickIds = useMemo(() => {
    const ids = new Set();
    Object.entries(picks || {}).forEach(([id, shares]) => {
      if (Number(shares) > 0) ids.add(String(id));
    });
    Object.entries(shareEditors || {}).forEach(([id, editor]) => {
      const n = Number(String(editor?.draft ?? '').trim());
      if (Number.isFinite(n) && n > 0) ids.add(String(id));
    });
    return ids;
  }, [picks, shareEditors]);
  const remainingSlots = Math.max(0, maxPortfolioSize - openPositionCount - activePickIds.size);
  const showEquityDelta = typeof equityDelta === 'number' && equityDelta !== 0;

  useEffect(() => {
    if (advancing) return;
    if (snapshot?.clockDate) setDisplayClockDate(snapshot.clockDate);
  }, [advancing, snapshot?.clockDate]);

  const calendarDays = useMemo(
    () => indexCalendarDays(snapshot?.calendar, shownClockDate),
    [snapshot?.calendar, shownClockDate],
  );
  const elapsedDays = useMemo(
    () => countTradingDaysInclusive(rangeStart, shownClockDate),
    [rangeStart, shownClockDate],
  );
  const totalDays = useMemo(
    () => countTradingDaysInclusive(rangeStart, rangeEnd),
    [rangeStart, rangeEnd],
  );
  const sessionPct = totalDays > 0 ? Math.min(100, (elapsedDays / totalDays) * 100) : 0;
  const canPrevMonth = canShiftMonth(viewYear, viewMonth, -1, rangeStart, rangeEnd);
  const canNextMonth = canShiftMonth(viewYear, viewMonth, 1, rangeStart, rangeEnd);

  const bill = useMemo(() => {
    const items = [];
    (snapshot?.opps || []).forEach((row) => {
      const shares = Number(picks[row.id] || 0);
      if (shares > 0) items.push({ ...row, shares, notional: shares * row.price });
    });
    return items;
  }, [snapshot?.opps, picks]);
  const billTotal = bill.reduce((sum, row) => sum + row.notional, 0);
  const cashOnHand = Number(snapshot?.cash) || 0;
  const billExceedsCash = billTotal > cashOnHand + 0.005;
  const holdingsByTicker = useMemo(() => {
    const map = {};
    holdings.forEach((row) => {
      const ticker = String(row.ticker || '').trim();
      if (ticker) map[ticker] = row;
    });
    return map;
  }, [holdings]);
  const oppRows = useMemo(
    () => (snapshot?.opps || []).map((opp) => {
      const held = holdingsByTicker[opp.ticker];
      return {
        ...opp,
        held: Boolean(held),
        heldBuyPrice: held?.buyPrice ?? null,
        heldShares: held?.shares ?? null,
        heldBuyDate: held?.buyDate || '',
      };
    }),
    [snapshot?.opps, holdingsByTicker],
  );

  const infoChart = useMemo(() => {
    if (!infoPayload?.candles?.length) return {};
    const markers = [];
    const buyYmd = String(infoOpp?.buyDate || infoOpp?.heldBuyDate || '').replace(/-/g, '');
    const clockYmd = String(clockDate || '').replace(/-/g, '');
    if (buyYmd) {
      markers.push({ type: 'buy', date: buyYmd, label: '买入' });
    }
    if (clockYmd && clockYmd !== buyYmd) {
      markers.push({ type: 'opportunity', date: clockYmd, label: '当前日' });
    }
    return buildStockKlineChartOptionFromPayload({
      candles: infoPayload.candles,
      indicator_series: infoPayload.indicatorSeries || [],
      markers,
    });
  }, [infoPayload, clockDate, infoOpp]);

  const holdingDetail = holdings.find((row) => row.id === holdingDetailId) || null;
  if (holdingDetail) holdingDetailCacheRef.current = holdingDetail;
  const holdingDialogRow = holdingDetail || holdingDetailCacheRef.current;

  const flushPicks = useCallback(async () => {
    if (pickTimerRef.current) {
      window.clearTimeout(pickTimerRef.current);
      pickTimerRef.current = null;
    }
    const pending = pendingPicksRef.current;
    pendingPicksRef.current = {};
    const dmId = snapshot?.dmId;
    if (!strategyKey || !dmId) return;
    const ids = Object.keys(pending);
    let last = snapshot;
    for (const id of ids) {
      last = await pickDecisionShares(strategyKey, dmId, {
        localId: Number(id),
        shares: Number(pending[id]) || 0,
      });
    }
    if (last && last !== snapshot) applyLive(last, undefined, { keepPicks: false });
  }, [applyLive, snapshot, strategyKey]);

  const schedulePick = (localId, shares) => {
    pendingPicksRef.current[localId] = shares;
    if (pickTimerRef.current) window.clearTimeout(pickTimerRef.current);
    pickTimerRef.current = window.setTimeout(() => {
      flushPicks().catch((err) => {
        const message = errorMessage(err, '无法下单');
        setToast(message);
        setShareEditors((prev) => ({
          ...prev,
          [localId]: {
            open: true,
            draft: prev[localId]?.draft ?? String(shares || ''),
            error: message,
          },
        }));
      });
    }, 400);
  };

  const updateShareDraft = (rowId, draft) => {
    setShareEditors((prev) => ({
      ...prev,
      [rowId]: { open: true, draft, error: '' },
    }));
  };

  const commitShareEditor = (row, rawValue) => {
    if (row.held) return;
    const editor = shareEditors[row.id];
    const picked = Number(picks[row.id] || 0);
    const raw = rawValue != null ? rawValue : (editor?.draft ?? (picked > 0 ? String(picked) : ''));
    const { minLot, lotStep } = lotRule(row);
    const result = validateShareDraft(raw, minLot, lotStep);
    if (!result.ok) {
      setShareEditors((prev) => ({
        ...prev,
        [row.id]: { open: true, draft: raw, error: result.message },
      }));
      setToast(result.message);
      return;
    }
    if (result.shares <= 0) {
      setShareEditors((prev) => {
        const next = { ...prev };
        delete next[row.id];
        return next;
      });
      setPicks((prev) => {
        const next = { ...prev };
        delete next[row.id];
        return next;
      });
      schedulePick(row.id, 0);
      return;
    }
    const occupying = Number(picks[row.id] || 0) > 0 || activePickIds.has(String(row.id));
    if (!occupying && remainingSlots <= 0) {
      setShareEditors((prev) => ({
        ...prev,
        [row.id]: { open: true, draft: raw, error: '已达组合上限' },
      }));
      setToast('已达组合上限');
      return;
    }
    setShareEditors((prev) => ({
      ...prev,
      [row.id]: { open: true, draft: String(result.shares), error: '' },
    }));
    schedulePick(row.id, result.shares);
  };

  const cancelShareEditor = (row) => {
    const picked = Number(picks[row.id] || 0);
    if (picked > 0) {
      setShareEditors((prev) => ({
        ...prev,
        [row.id]: { open: true, draft: String(picked), error: '' },
      }));
      return;
    }
    setShareEditors((prev) => {
      const next = { ...prev };
      delete next[row.id];
      return next;
    });
  };

  const stepShareEditor = (row, direction) => {
    if (row.held) return;
    const { minLot, lotStep } = lotRule(row);
    const editor = shareEditors[row.id];
    const current = editor?.draft != null && String(editor.draft).trim() !== ''
      ? editor.draft
      : (picks[row.id] || 0);
    const next = stepShares(current, direction, minLot, lotStep);
    const draft = next > 0 ? String(next) : '';
    setShareEditors((prev) => ({
      ...prev,
      [row.id]: { open: true, draft, error: '' },
    }));
    commitShareEditor(row, draft);
  };

  const applySuggestedShares = (row) => {
    const shares = Number(row.suggestedShares) || 0;
    if (row.held || shares <= 0) return;
    const occupying = Number(picks[row.id] || 0) > 0 || activePickIds.has(String(row.id));
    if (!occupying && remainingSlots <= 0) {
      setToast('已达组合上限');
      return;
    }
    setShareEditors((prev) => ({
      ...prev,
      [row.id]: { open: true, draft: String(shares), error: '' },
    }));
    schedulePick(row.id, shares);
  };

  const openInfo = async (row) => {
    setInfoOpp(row);
    setInfoPayload(null);
    if (!strategyKey || !snapshot?.dmId || !row) return;
    setInfoLoading(true);
    try {
      const payload = await fetchDecisionInfo(strategyKey, snapshot.dmId, {
        target: String(row.ticker || row.id || ''),
      });
      setInfoPayload(payload);
    } catch (err) {
      setToast(errorMessage(err, '无法加载 info'));
    } finally {
      setInfoLoading(false);
    }
  };

  const shareDisabled = completed || advancing;
  const slotLocked = (row) => {
    if (!row || row.held) return true;
    if (shareDisabled) return true;
    if (activePickIds.has(String(row.id))) return false;
    return remainingSlots <= 0;
  };
  const oppColumns = [
    { field: 'id', headerName: '#', width: 56 },
    {
      field: 'stock',
      headerName: '股票',
      minWidth: 200,
      flex: 1.2,
      valueGetter: (p) => opportunityStockLabel(p.row),
      renderCell: (grid) => (
        <span className="decision-opp-stock-cell">
          <span className="decision-opp-stock-line">
            <button
              type="button"
              className="decision-opp-stock"
              onClick={() => openInfo(grid.row)}
            >
              {opportunityStockLabel(grid.row)}
            </button>
            <StockStatusChips tags={grid.row.statusTags} />
          </span>
          {grid.row.held ? (
            <span className="decision-opp-held">
              持有中
              {grid.row.heldBuyPrice != null ? ` · 上次买入 ${formatMoney(grid.row.heldBuyPrice)}` : ''}
            </span>
          ) : null}
        </span>
      ),
    },
    {
      field: 'price',
      headerName: '成交价',
      width: 96,
      valueFormatter: (p) => formatMoney(p.value),
    },
    {
      field: 'wr',
      width: 108,
      renderHeader: headerWithTooltip(
        '模拟胜率',
        '该标的在当前日之前已经完成的枚举记录胜率（exit_date < 当天）。无样本为 —。',
      ),
    },
    {
      field: 'roi',
      width: 108,
      renderHeader: headerWithTooltip(
        '模拟 ROI',
        '该标的在当前日之前已经完成的枚举记录平均 ROI。无样本为 —。',
      ),
    },
    {
      field: 'suggestedShares',
      width: 168,
      sortable: false,
      renderHeader: headerWithTooltip(
        '建议买入',
        suggestedBuyTooltip(snapshot?.allocationMode),
      ),
      renderCell: (grid) => (
        <SuggestedSharesCell
          suggestedCash={grid.row.suggestedCash}
          suggestedShares={grid.row.suggestedShares}
          basis={grid.row.suggestedBasis}
          held={grid.row.held}
          disabled={slotLocked(grid.row)}
          onApply={() => applySuggestedShares(grid.row)}
        />
      ),
    },
    {
      field: 'shares',
      headerName: '投资',
      width: 252,
      minWidth: 252,
      sortable: false,
      renderCell: (grid) => {
        if (grid.row.held) {
          return <Chip size="small" variant="outlined" label="已持有" />;
        }
        const editor = shareEditors[grid.row.id];
        const pickedShares = Number(picks[grid.row.id] || 0);
        const draft = editor?.draft ?? (pickedShares > 0 ? String(pickedShares) : '');
        const parsed = Number(draft);
        const notional = Number.isFinite(parsed) && parsed > 0
          ? formatMoney(cashFromShares(parsed, grid.row.price))
          : '';
        const { lotStep } = lotRule(grid.row);
        return (
          <SharesInvestCell
            disabled={slotLocked(grid.row)}
            draft={draft}
            error={editor?.error || ''}
            notional={notional}
            ticker={grid.row.ticker}
            lotStep={lotStep}
            onDraftChange={(value) => updateShareDraft(grid.row.id, value)}
            onCommit={(raw) => commitShareEditor(grid.row, raw)}
            onCancel={() => cancelShareEditor(grid.row)}
            onStep={(direction) => stepShareEditor(grid.row, direction)}
          />
        );
      },
    },
  ];

  const sleep = (ms) => new Promise((resolve) => {
    animRef.current.timer = window.setTimeout(resolve, ms);
  });

  const openCalendar = () => {
    if (calendarOpen) {
      setCalendarOpen(false);
      return;
    }
    const month = dateToYearMonth(clockDate);
    setViewYear(month.year);
    setViewMonth(month.month);
    setCalendarOpen(true);
  };

  const closeCalendar = () => {
    setCalendarOpen(false);
  };

  const resumePicking = useCallback(async () => {
    const dmId = snapshot?.dmId;
    if (!strategyKey || !dmId) return null;
    const snap = await resetDecisionDraft(strategyKey, dmId, { keepDraft: true });
    applyLive(snap, undefined, { keepPicks: true });
    return snap;
  }, [applyLive, snapshot?.dmId, strategyKey]);

  const cancelConfirm = useCallback(() => {
    setConfirmOpen(false);
    if (snapshot?.phase !== 'confirming') return;
    resumePicking().catch((err) => {
      setToast(errorMessage(err, '无法返回查看'));
    });
  }, [resumePicking, snapshot?.phase]);

  const runAdvance = async () => {
    if (!strategyKey || !snapshot?.dmId || completed || advancing) return;
    if (billExceedsCash) {
      setToast(`现金不足，可用 ${formatMoney(cashOnHand)} 元，本单约 ${formatMoney(billTotal)} 元`);
      return;
    }
    closeCalendar();
    try {
      if (snapshot.phase !== 'confirming') {
        await flushPicks();
        await doneDecisionDay(strategyKey, snapshot.dmId);
      }
      const nextSnap = await nextDecisionDay(strategyKey, snapshot.dmId);
      setConfirmOpen(false);
      const fromDate = snapshot.clockDate || displayClockDate;
      setAdvancing(true);
      setClockMotion('is-out');
      const held = await loadHoldings(nextSnap.dmId);
      const hops = listOpenDaysAfter(fromDate, nextSnap.clockDate);
      if (!prefersReducedMotion() && hops.length) {
        for (const date of hops) {
          if (animRef.current.cancelled) return;
          setClockMotion('is-out');
          await sleep(CLOCK_FADE_OUT_MS);
          if (animRef.current.cancelled) return;
          setDisplayClockDate(date);
          setClockMotion('is-in');
          await sleep(Math.max(CLOCK_STEP_MS - CLOCK_FADE_OUT_MS, 200));
        }
      } else {
        setDisplayClockDate(nextSnap.clockDate || fromDate);
      }
      applyLive(nextSnap, held, { hopEvents: nextSnap.events || [], keepPicks: false });
      setClockMotion('is-landed');
      setAdvancing(false);
      setToast(nextSnap.completed ? '本局已走完' : '已提交当天，停在下一事件日');
    } catch (err) {
      setClockMotion('is-landed');
      setAdvancing(false);
      try {
        await resumePicking();
      } catch {
        /* 返回可改状态失败时仍提示推进错误 */
      }
      setToast(errorMessage(err, '推进失败'));
    }
  };
  runAdvanceRef.current = runAdvance;

  const requestAdvance = () => {
    if (completed || advancing) return;
    if (hasOpps) {
      setConfirmOpen(true);
      return;
    }
    runAdvance();
  };

  useEffect(() => {
    const isSpace = (event) => event.code === 'Space' || event.key === ' ';
    const onKeyDown = (event) => {
      if (!isSpace(event) || event.repeat) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target;
      if (target?.closest?.('input, textarea, [contenteditable="true"]')) return;
      if (infoOpp || holdingDetailId) return;
      if (completed || advancing) {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      if (spaceLockRef.current) return;
      spaceLockRef.current = true;
      if (confirmOpen || !hasOpps) {
        runAdvanceRef.current?.();
        return;
      }
      setConfirmOpen(true);
    };
    const onKeyUp = (event) => {
      if (isSpace(event)) spaceLockRef.current = false;
    };
    window.addEventListener('keydown', onKeyDown, true);
    window.addEventListener('keyup', onKeyUp, true);
    return () => {
      window.removeEventListener('keydown', onKeyDown, true);
      window.removeEventListener('keyup', onKeyUp, true);
    };
  }, [advancing, completed, confirmOpen, hasOpps, holdingDetailId, infoOpp]);

  if (!pageReady && !loadError) {
    if (embedded) {
      return render({
        loading: true,
        error: '',
        hud: null,
        status: null,
        board: null,
        dialogs: null,
        completed: false,
      });
    }
    return (
      <PageLayout
        className="decision-page"
        breadcrumbsItems={[{ label: '制定策略', to: designHref }]}
        breadcrumbsCurrent="对局"
        bannerTitle="决策者对局"
        bannerDescription="正在打开这一局。"
      >
        <InlineLoadingState block message="正在加载对局现场…" />
      </PageLayout>
    );
  }

  if (loadError || !snapshot) {
    if (embedded) {
      return render({
        loading: false,
        error: loadError || '对局不存在',
        hud: null,
        status: null,
        board: null,
        dialogs: null,
        completed: false,
      });
    }
    return (
      <PageLayout
        className="decision-page"
        breadcrumbsItems={[{ label: '制定策略', to: designHref }]}
        breadcrumbsCurrent="对局"
        bannerTitle="决策者对局"
        bannerDescription="无法打开这一局。"
        bannerRightSlot={(
          <Button component={RouterLink} to={designHref} variant="outlined" size="small">
            返回制定策略
          </Button>
        )}
      >
        <Alert severity="error" variant="outlined">{loadError || '对局不存在'}</Alert>
      </PageLayout>
    );
  }

  const asof = snapshot.asof;
  const strategyWin = asof?.winRateLabel || '—';
  const strategyRoi = asof?.avgRoiLabel || '—';
  const rangeLabel = rangeStart && rangeEnd ? `${rangeStart} → ${rangeEnd}` : '—';

  const clockHud = (
    <Box className={`decision-hud${embedded ? ' decision-hud--embedded' : ''}`} aria-label="对局时钟">
      <Box className="decision-hud-main">
        <Box className="decision-calendar-block" data-ntq-help="decision-clock">
          <Typography className="decision-calendar-title" component="h2">
            交易日历
          </Typography>
          <Box className={`decision-clock ${clockMotion}`}>
            <Typography className="decision-clock__date">{shownClockDate || '—'}</Typography>
            <Typography className="decision-clock__weekday">{weekdayLabel(shownClockDate)}</Typography>
          </Box>
        </Box>

        <Box className="decision-hud-actions" data-ntq-help="decision-advance">
          {completed && typeof onViewReport === 'function' ? (
            <Button
              className="decision-advance-btn"
              variant="contained"
              onClick={onViewReport}
            >
              查看报告
            </Button>
          ) : (
            <Button
              className="decision-advance-btn"
              variant="contained"
              disabled={completed || advancing}
              startIcon={<NtqIcon name="play" size={16} />}
              onClick={requestAdvance}
              title="空格也可推进"
              aria-keyshortcuts="Space"
            >
              {advancing ? '推进中' : '下一个事件（空格键）'}
            </Button>
          )}
          <Button
            variant="outlined"
            className="decision-calendar-toggle"
            aria-haspopup="dialog"
            aria-expanded={calendarOpen}
            onClick={openCalendar}
          >
            事件回溯
          </Button>
        </Box>

        <Box className="decision-hud-metrics" data-ntq-help="decision-metrics">
          <Box className="decision-hud-metric">
            <Typography variant="caption" color="text.secondary">账户价值</Typography>
            <Typography variant="h6" className="decision-hud-metric__value">
              {formatMoney(equity)}
              {showEquityDelta ? (
                <Box
                  component="span"
                  className={`decision-hud-delta ${equityDelta >= 0 ? 'is-up' : 'is-down'}`}
                >
                  （{formatSignedMoney(equityDelta)}）
                </Box>
              ) : null}
            </Typography>
          </Box>
          <Box className="decision-hud-metric">
            <Typography variant="caption" color="text.secondary">可用资金</Typography>
            <Typography variant="h6" className="decision-hud-metric__value">
              {formatMoney(snapshot.cash)}
              <Box component="span" className="decision-hud-ratio">
                {' '}
                ({formatPct(cashRatio)})
              </Box>
            </Typography>
          </Box>
        </Box>
      </Box>

      <Box className="decision-progress">
        <Box
          className="decision-progress__track"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(sessionPct)}
          aria-label="回测进度"
        >
          <Box className="decision-progress__fill" style={{ width: `${sessionPct}%` }} />
        </Box>
        <Typography className="decision-progress__label" variant="caption">
          {totalDays > 0
            ? `已走 ${elapsedDays} / ${totalDays} 个交易日`
            : (shownClockDate ? `停在 ${shownClockDate}` : '区间未知')}
        </Typography>
      </Box>
    </Box>
  );

  const playInner = (
    <>
      {completed ? (
        <Alert severity="warning" variant="outlined" sx={{ mb: 2 }}>
          本局已走完，只读回看。不能改股数，也不能再推进。
        </Alert>
      ) : null}

      {embedded ? null : (
      <Card variant="outlined" className="decision-hud-card" sx={{ mb: 2 }}>
        <CardContent>
          {clockHud}
        </CardContent>
      </Card>
      )}

      <Dialog
        open={calendarOpen}
        onClose={closeCalendar}
        maxWidth={false}
        scroll="paper"
        PaperProps={{ className: 'decision-month-popover' }}
      >
        <Box className="decision-month">
          <Box className="decision-month-nav">
            <IconButton
              size="small"
              aria-label="上个月"
              disabled={!canPrevMonth}
              onClick={() => {
                const next = shiftMonth(viewYear, viewMonth, -1);
                setViewYear(next.year);
                setViewMonth(next.month);
              }}
            >
              <NtqIcon name="arrowBack" size={16} />
            </IconButton>
            <Typography className="decision-month-title">{monthTitle(viewYear, viewMonth)}</Typography>
            <IconButton
              size="small"
              aria-label="下个月"
              disabled={!canNextMonth}
              onClick={() => {
                const next = shiftMonth(viewYear, viewMonth, 1);
                setViewYear(next.year);
                setViewMonth(next.month);
              }}
            >
              <NtqIcon name="chevronRight" size={16} />
            </IconButton>
          </Box>
          {calendarOpen ? (
            <MonthGrid
              year={viewYear}
              month={viewMonth}
              clockDate={clockDate}
              days={calendarDays}
              rangeStart={rangeStart}
              rangeEnd={rangeEnd}
            />
          ) : null}
          <Typography className="decision-month-legend" variant="caption">
            <span className="decision-month-legend__now">当前停顿日</span>
            <span className="decision-month-legend__opp">发现机会</span>
            <span className="decision-month-legend__buy">买入</span>
            <span className="decision-month-legend__sell">卖出</span>
            未来日期不标注 · 不能点选跳转
          </Typography>
        </Box>
      </Dialog>

      <Box className={`decision-play-split ${advancing ? 'is-advancing' : ''}`}>
        <Box className="decision-left">
          <Card variant="outlined">
            <CardContent className="decision-aside">
              {hideStrategyMeta ? null : (
              <Box className="decision-aside-section">
                <Typography className="decision-aside-title" variant="subtitle1" fontWeight={700}>
                  策略与模拟
                </Typography>
                {[
                  ['策略', snapshot.strategyKey || strategyKey],
                  ['版本', snapshot.versionId || '—'],
                  ['对局', String(snapshot.dmId)],
                  ['回测区间', rangeLabel],
                  ['最大同时持有数', String(snapshot.maxPortfolioSize || '—')],
                ].map(([label, value]) => (
                  <Typography key={label} className="decision-kv" variant="body2">
                    <span className="decision-kv__label">{label}</span>
                    <span className="decision-kv__value">{value}</span>
                  </Typography>
                ))}
              </Box>
              )}

              <Box className="decision-aside-section" data-ntq-help="decision-holdings">
                <Typography className="decision-aside-title" variant="subtitle1" fontWeight={700}>
                  持仓状态
                </Typography>
                <Typography className="decision-kv" variant="body2">
                  <span className="decision-kv__label">持仓市值</span>
                  <span className="decision-kv__value">{formatMoney(holdingsValue)}</span>
                </Typography>
                {holdings.length ? (
                  <>
                    <Box className="decision-holding-head">
                      <span>股票</span>
                      <span>持有</span>
                      <span>盈亏</span>
                    </Box>
                    <Box className="decision-holding-list">
                      {holdings.map((row) => (
                        <button
                          key={row.id}
                          type="button"
                          className="decision-holding-row"
                          onClick={() => setHoldingDetailId(row.id)}
                        >
                          <span className="decision-holding-row__stock">
                            <strong>
                              {row.name || row.ticker || '—'}
                              <StockStatusChips tags={row.statusTags} />
                            </strong>
                            {row.name && row.ticker ? <span>{row.ticker}</span> : null}
                          </span>
                          <span className="decision-holding-row__qty">
                            {Number(row.shares).toLocaleString()} 股
                          </span>
                          <span className={`decision-holding-row__pnl decision-pnl ${
                            row.unrealized == null || !Number.isFinite(Number(row.unrealized))
                              ? ''
                              : holdingPnlTone(row.unrealized)
                          }`}
                          >
                            {formatHoldingListPnl(row.unrealized)}
                          </span>
                        </button>
                      ))}
                    </Box>
                    <Typography variant="caption" color="text.secondary" className="decision-holding-hint">
                      点一行查看明细
                    </Typography>
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary">当前无持仓</Typography>
                )}
              </Box>

              <Box className="decision-aside-section">
                <button
                  type="button"
                  className={`decision-aside-fold${positionOpen ? ' is-open' : ''}`}
                  aria-expanded={positionOpen}
                  onClick={() => setPositionOpen((open) => !open)}
                >
                  <Typography className="decision-aside-title" variant="subtitle1" fontWeight={700}>
                    约束条件与状态统计
                  </Typography>
                  <NtqIcon name="expandMore" size={20} />
                </button>
                {positionOpen ? (
                  <>
                    {[
                      ['持仓 / 上限', `${snapshot.openPositionCount} / ${snapshot.maxPortfolioSize || '—'}`],
                      ['至今最大回撤', formatDrawdown(null)],
                      ['策略至今胜率', strategyWin],
                      ['策略平均回报率', strategyRoi],
                    ].map(([label, value]) => (
                      <Typography key={label} className="decision-kv" variant="body2">
                        <span className="decision-kv__label">{label}</span>
                        <span className="decision-kv__value">{value}</span>
                      </Typography>
                    ))}
                  </>
                ) : null}
              </Box>
            </CardContent>
          </Card>
        </Box>

        <Box className="decision-right">
          <Card variant="outlined" data-ntq-help="decision-events">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>今日事件</Typography>
              {events.length ? (
                <Stack spacing={1}>
                  {events.map((row) => (
                    <Box
                      key={`${row.date}-${row.ticker}-${row.shares}`}
                      className={`decision-event ${row.win ? 'is-win' : 'is-loss'}`}
                    >
                      <Typography variant="caption" color="text.secondary">{row.date}</Typography>
                      <Typography variant="body2">{row.text}</Typography>
                    </Box>
                  ))}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  今日无出场结算。
                </Typography>
              )}
            </CardContent>
          </Card>

          <Card
            variant="outlined"
            className={hasOpps ? 'decision-opp-card is-hot' : 'decision-opp-card'}
            data-ntq-help="decision-opps"
          >
            <CardContent>
              <Box className="decision-opp-head">
                <Typography
                  className={`decision-opp-title ${hasOpps ? 'is-hot' : 'is-empty'}`}
                  component="h2"
                >
                  {hasOpps ? '发现了新的可交易机会' : '今日没有可交易的机会'}
                </Typography>
                {hasOpps ? (
                  <Typography className="decision-opp-meta">
                    点击股票名称查看当前状态。还可选择
                    {' '}
                    <span className="decision-opp-slots">{remainingSlots}</span>
                    {' '}
                    个机会
                    {remainingSlots <= 0 ? (
                      <span className="decision-opp-slots-full">（已达组合上限）</span>
                    ) : null}
                  </Typography>
                ) : null}
              </Box>
              {hasOpps ? (
                <DataGrid
                  autoHeight
                  rows={oppRows}
                  columns={oppColumns}
                  localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
                  hideFooter
                  disableRowSelectionOnClick
                  onCellClick={(params, event) => {
                    if (event.target.closest('.decision-invest-cell, .decision-suggest-apply')) {
                      event.stopPropagation();
                    }
                  }}
                  getRowClassName={(params) => {
                    const classes = [];
                    if (params.row.held) classes.push('is-held');
                    if (slotLocked(params.row) && !params.row.held) classes.push('is-capped');
                    return classes.join(' ');
                  }}
                  getRowHeight={(params) => {
                    const row = oppRows.find((item) => item.id === params.id);
                    return row?.held ? 64 : 56;
                  }}
                  sx={{
                    border: 0,
                    '& .MuiDataGrid-row:hover': {
                      backgroundColor: 'rgba(34, 211, 238, 0.06)',
                    },
                    '& .MuiDataGrid-cell': { outline: 'none', overflow: 'visible' },
                  }}
                />
              ) : null}
            </CardContent>
          </Card>
        </Box>
      </Box>

      <HoldingDetailDialog
        open={Boolean(holdingDetail)}
        row={holdingDialogRow}
        equity={equity}
        onClose={() => setHoldingDetailId(null)}
        onOpenKline={holdingDialogRow ? () => {
          const row = holdingDialogRow;
          setHoldingDetailId(null);
          openInfo({
            ticker: row.ticker,
            name: row.name,
            wr: '—',
            roi: '—',
            buyDate: row.buyDate,
          });
        } : undefined}
      />

      <Dialog open={confirmOpen} onClose={cancelConfirm} maxWidth="sm" fullWidth>
        <DialogTitle>确认当天选择</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            提交后不可改当日选择。空选择等于本日不买。空格确认后，日历会按交易日走到下一事件。
          </Typography>
          {bill.length ? (
            bill.map((row) => (
              <Stack
                key={row.id}
                direction="row"
                justifyContent="space-between"
                sx={{ py: 0.5 }}
              >
                <Typography variant="body2" component="div" className="decision-stock-with-status">
                  [{row.id}] {row.name} <StockStatusChips tags={row.statusTags} /> {row.shares.toLocaleString()} 股
                </Typography>
                <Typography variant="body2">约 {formatMoney(row.notional)}</Typography>
              </Stack>
            ))
          ) : (
            <Typography variant="body2">当前选择：（空，本日不买）</Typography>
          )}
          <Stack direction="row" justifyContent="space-between" sx={{ mt: 1.5, pt: 1.5, borderTop: 1, borderColor: 'divider' }}>
            <Typography color="text.secondary">可用资金</Typography>
            <Typography>{formatMoney(cashOnHand)} 元</Typography>
          </Stack>
          <Stack direction="row" justifyContent="space-between" sx={{ mt: 0.5 }}>
            <Typography fontWeight={700}>合计（约）</Typography>
            <Typography fontWeight={700} color={billExceedsCash ? 'error' : 'inherit'}>
              {formatMoney(billTotal)} 元
            </Typography>
          </Stack>
          {billExceedsCash ? (
            <Alert severity="warning" variant="outlined" sx={{ mt: 1.5 }}>
              这几笔加起来超过可用资金。返回查看后减少买入，或卖掉持仓后再买。
            </Alert>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelConfirm}>返回查看</Button>
          <Button
            variant="contained"
            onClick={runAdvance}
            disabled={advancing || billExceedsCash}
          >
            确认推进（空格键）
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(infoOpp)}
        onClose={() => setInfoOpp(null)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, pr: 1 }}>
          <span className="decision-stock-with-status">
            {infoOpp ? opportunityStockLabel(infoOpp) : 'K 线'}
            {infoOpp ? <StockStatusChips tags={infoOpp.statusTags} /> : null}
          </span>
          <IconButton aria-label="关闭" onClick={() => setInfoOpp(null)}>
            <NtqIcon name="cancel" size={18} />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {infoOpp ? (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                as-of {clockDate} · 前复权 K 线停在当前日，不含未来
                {infoPayload?.indicatorSeries?.some((row) => row.panel === 'oscillator')
                  ? ` · 副图：${infoPayload.indicatorSeries
                    .filter((row) => row.panel === 'oscillator')
                    .map((row) => row.label || row.key)
                    .filter(Boolean)
                    .join('、')}`
                  : ''}
              </Typography>
              <Stack spacing={0.75} sx={{ mb: 2 }}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">策略 as-of</Typography>
                  <Typography variant="body2">
                    胜率 {strategyWin}  平均ROI {strategyRoi}
                    {asof?.sampleSize != null ? `  n=${asof.sampleSize}` : ''}
                  </Typography>
                </Stack>
                <Stack direction="row" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">本标的 as-of</Typography>
                  <Typography variant="body2">
                    胜率 {infoPayload?.tickerStats?.winRateLabel || infoOpp.wr}
                    {' '}
                    平均ROI {infoPayload?.tickerStats?.avgRoiLabel || infoOpp.roi}
                  </Typography>
                </Stack>
              </Stack>
              {infoLoading ? (
                <InlineLoadingState block message="正在加载 K 线…" />
              ) : (
                <ChartPanel
                  title="K 线"
                  option={infoChart}
                  height={560}
                  note={infoPayload?.candles?.length
                    ? '主图：K线（前复权）与策略声明指标。买入日有标记。使用底部滑块调整可见区间。'
                    : '没有截至当前日的 K 线。'}
                />
              )}
            </>
          ) : null}
        </DialogContent>
      </Dialog>

      <Snackbar
        open={Boolean(toast)}
        autoHideDuration={2800}
        onClose={() => setToast('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity="info" variant="outlined" onClose={() => setToast('')}>
          {toast}
        </Alert>
      </Snackbar>
    </>
  );

  if (embedded) {
    return render({
      loading: false,
      error: '',
      inner: playInner,
      hud: clockHud,
      completed,
      snapshot,
      advancing,
      requestAdvance,
    });
  }

  return (
    <PageLayout
      className="decision-page"
      breadcrumbsItems={[{ label: '制定策略', to: designHref }]}
      breadcrumbsCurrent={`第 ${snapshot.dmId} 局`}
      bannerTitle={`决策模拟 · 第 ${snapshot.dmId} 局`}
      bannerDescription="时钟只显示当前停顿日。推进后总进度前移；月历是只读地图，只标注已经发生的事件。"
      bannerRightSlot={(
        <Button component={RouterLink} to={designHref} variant="outlined" size="small">
          返回制定策略
        </Button>
      )}
    >
      {playInner}
    </PageLayout>
  );
}
