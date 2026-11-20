import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, ChartPanel, DataGrid, DefinitionList, Dialog, Icon, Message, Tag, Loading, showToast } from 'ui';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import PageLayout from 'ntq-ui/pageLayout';
import {
  buildMarketChartOptionFromStockPayload,
  FinancePitCard,
  pickFinanceSnapshot,
  resolveAxisPointerDate,
  stockKlinePayloadToMarketChartModel,
} from 'containers/marketChart';
import {
  doneDecisionDay,
  fetchDecisionHoldings,
  fetchDecisionInfo,
  fetchDecisionSession,
  fetchDecisionStockStatus,
  holdingsMarketValue,
  nextDecisionDay,
  pickDecisionShares,
  resetDecisionDraft,
} from '../../api/decisionApi';
import { getStrategyDesignPath } from '../../api/strategyApi';
import {
  canShiftMonth,
  countTradingDaysInclusive,
  dateToYearMonth,
  formatMoney,
  formatPct,
  formatSignedMoney,
  indexCalendarDays,
  listOpenDaysAfter,
  monthTitle,
  plannedGoalLevelsForChart,
  shiftMonth,
  weekdayLabel,
} from './decisionFormat';
import {
  errorMessage,
  formatDrawdown,
  formatHoldingListPnl,
  headerWithTooltip,
  holdingPnlTone,
  lotRule,
  opportunityStockLabel,
  prefersReducedMotion,
  resolveLiveStatus,
  stepShares,
  StockStatusChips,
  suggestedBuyTooltip,
  validateShareDraft,
} from './decisionPlayHelpers';
import {
  InvestDialog,
  InvestOpenCell,
  NOTE_MAX,
  SuggestedSharesCell,
} from './investControls';
import { HoldingDetailDialog } from './holdingDetailDialog';
import { CalendarActionDialog, MonthGrid } from './calendarWidgets';
import './style.scss';

const CLOCK_STEP_MS = 300;
const CLOCK_FADE_OUT_MS = 100;

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
  const [liveStatusById, setLiveStatusById] = useState({});
  const [statusLoading, setStatusLoading] = useState(false);
  const [picks, setPicks] = useState({});
  const [pickNotes, setPickNotes] = useState({});
  const [events, setEvents] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [pageReady, setPageReady] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [holdingDetailId, setHoldingDetailId] = useState(null);
  const [infoOpp, setInfoOpp] = useState(null);
  const [infoPayload, setInfoPayload] = useState(null);
  const [infoLoading, setInfoLoading] = useState(false);
  const [infoPointerAsOf, setInfoPointerAsOf] = useState('');
  const infoZoomEndRef = useRef('');
  const [investRow, setInvestRow] = useState(null);
  const [investShares, setInvestShares] = useState('');
  const [investNote, setInvestNote] = useState('');
  const [investError, setInvestError] = useState('');
  const [investBusy, setInvestBusy] = useState(false);
  const [calendarAction, setCalendarAction] = useState(null);
  const [positionOpen, setPositionOpen] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [displayClockDate, setDisplayClockDate] = useState('');
  const [clockMotion, setClockMotion] = useState('is-landed');
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [viewYear, setViewYear] = useState(() => dateToYearMonth('').year);
  const [viewMonth, setViewMonth] = useState(() => dateToYearMonth('').month);
  const animRef = useRef({ cancelled: false, timer: null });
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
      setPickNotes(snap.pickNotes || {});
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
        setLoadError('缺少策略或模拟回测');
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
        if (!cancelled) setLoadError(errorMessage(err, '无法打开模拟回测'));
      } finally {
        if (!cancelled) setPageReady(true);
      }
    })();

    return () => {
      cancelled = true;
      anim.cancelled = true;
      if (anim.timer) window.clearTimeout(anim.timer);
    };
  }, [strategyKey, sessionId, embedded, applyLive, loadHoldings]);

  const clockDate = snapshot?.clockDate || '';
  const shownClockDate = displayClockDate || clockDate;
  const statusEntityIds = useMemo(() => {
    const ids = new Set();
    (snapshot?.opps || []).forEach((row) => {
      const id = String(row?.ticker || '').trim();
      if (id) ids.add(id);
    });
    (holdings || []).forEach((row) => {
      const id = String(row?.ticker || '').trim();
      if (id) ids.add(id);
    });
    (snapshot?.bill || []).forEach((row) => {
      const id = String(row?.ticker || '').trim();
      if (id) ids.add(id);
    });
    const infoId = String(infoOpp?.ticker || infoPayload?.entityId || '').trim();
    if (infoId) ids.add(infoId);
    return Array.from(ids).sort();
  }, [snapshot?.opps, snapshot?.bill, holdings, infoOpp?.ticker, infoPayload?.entityId]);

  useEffect(() => {
    if (!strategyKey || !clockDate || !statusEntityIds.length) {
      setLiveStatusById({});
      setStatusLoading(false);
      return undefined;
    }
    let cancelled = false;
    setLiveStatusById({});
    setStatusLoading(true);
    (async () => {
      try {
        const result = await fetchDecisionStockStatus(strategyKey, {
          stockIds: statusEntityIds,
          date: clockDate,
        });
        if (cancelled) return;
        setLiveStatusById(result.statuses || {});
      } catch {
        if (!cancelled) setLiveStatusById({});
      } finally {
        if (!cancelled) setStatusLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [strategyKey, clockDate, statusEntityIds]);

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
    return ids;
  }, [picks]);
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
      if (shares > 0) items.push({
        ...row,
        shares,
        notional: shares * row.price,
        note: String(pickNotes[row.id] || '').trim(),
      });
    });
    return items;
  }, [snapshot?.opps, picks, pickNotes]);
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

  const infoHoldingGoals = useMemo(() => {
    if (Array.isArray(infoOpp?.goals) && infoOpp.goals.length) return infoOpp.goals;
    const ticker = String(infoOpp?.ticker || '').trim();
    if (!ticker) return null;
    const buyDate = String(infoOpp?.buyDate || infoOpp?.heldBuyDate || '').trim();
    const matched = (holdings || []).find((row) => {
      if (String(row.ticker || '') !== ticker) return false;
      if (!buyDate) return true;
      return String(row.buyDate || '') === buyDate
        || String(row.buyDate || '').replace(/-/g, '') === buyDate.replace(/-/g, '');
    });
    return matched?.goals || holdingsByTicker[ticker]?.goals || null;
  }, [infoOpp, holdings, holdingsByTicker]);

  const infoBuyPrice = useMemo(() => {
    if (infoOpp?.buyPrice != null && Number.isFinite(Number(infoOpp.buyPrice))) {
      return Number(infoOpp.buyPrice);
    }
    if (infoOpp?.heldBuyPrice != null && Number.isFinite(Number(infoOpp.heldBuyPrice))) {
      return Number(infoOpp.heldBuyPrice);
    }
    const ticker = String(infoOpp?.ticker || '').trim();
    const held = ticker ? holdingsByTicker[ticker] : null;
    return held?.buyPrice != null && Number.isFinite(Number(held.buyPrice))
      ? Number(held.buyPrice)
      : null;
  }, [infoOpp, holdingsByTicker]);

  const infoChartHeight = useMemo(() => {
    let panes = 1;
    const candles = infoPayload?.candles || [];
    if (candles.some((row) => row?.volume != null && Number.isFinite(Number(row.volume)))) {
      panes += 1;
    }
    const subKeys = new Set();
    (infoPayload?.indicatorSeries || []).forEach((row) => {
      const panel = String(row?.panel || 'overlay');
      if (!panel || panel === 'overlay') return;
      subKeys.add(String(row?.pane_group || row?.paneGroup || panel));
    });
    panes += subKeys.size;
    (infoPayload?.chartLayers || []).forEach((layer) => {
      const role = String(layer?.role || '');
      if (role === 'macro_step') panes += 1;
      if (role === 'state_lane') {
        panes += Math.max(1, (layer?.lanes || []).length || 1);
      }
    });
    // 主图 + 每张附图留足高度，避免 CMF / GDP 被压成一条缝
    return Math.max(560, 280 + panes * 130);
  }, [infoPayload]);

  const infoChart = useMemo(() => {
    if (!infoPayload?.candles?.length) return {};
    const markers = [];
    const buyYmd = String(infoOpp?.buyDate || infoOpp?.heldBuyDate || '').replace(/-/g, '');
    const clockYmd = String(clockDate || '').replace(/-/g, '');
    if (buyYmd) {
      markers.push({ type: 'buy', date: buyYmd, label: '买入' });
    }
    if (clockYmd && clockYmd !== buyYmd) {
      markers.push({ type: 'current_day', date: clockYmd, label: '当前日' });
    }
    const fromApi = Array.isArray(infoPayload.plannedLevels) && infoPayload.plannedLevels.length
      ? infoPayload.plannedLevels
      : null;
    const fromGoals = plannedGoalLevelsForChart({
      candles: infoPayload.candles,
      buyDate: buyYmd,
      goals: infoHoldingGoals,
      buyPrice: infoBuyPrice,
    });
    return buildMarketChartOptionFromStockPayload({
      candles: infoPayload.candles,
      indicator_series: infoPayload.indicatorSeries || [],
      chart_layers: infoPayload.chartLayers || [],
      markers,
      hoverGoalLevels: fromApi || fromGoals,
    });
  }, [infoPayload, clockDate, infoOpp, infoHoldingGoals, infoBuyPrice]);

  const infoChartModel = useMemo(
    () => stockKlinePayloadToMarketChartModel({
      candles: infoPayload?.candles || [],
      indicator_series: infoPayload?.indicatorSeries || [],
      chart_layers: infoPayload?.chartLayers || [],
      markers: [],
    }),
    [infoPayload],
  );

  const infoHasFinanceLayer = useMemo(() => {
    if ((infoChartModel?.financeEvents || []).length > 0) return true;
    return (infoPayload?.chartLayers || []).some((l) => String(l?.role || '') === 'event_pins');
  }, [infoChartModel, infoPayload]);

  const infoFinanceSnapshot = useMemo(() => {
    const events = infoChartModel?.financeEvents;
    if (!infoPointerAsOf || !events?.length) return null;
    return pickFinanceSnapshot(events, infoPointerAsOf);
  }, [infoChartModel, infoPointerAsOf]);

  const infoFinanceLive = Boolean(infoPointerAsOf && infoFinanceSnapshot);

  const infoCandleDates = useMemo(
    () => (infoPayload?.candles || []).map((c) => String(c?.date || '').trim()).filter(Boolean),
    [infoPayload],
  );

  useEffect(() => {
    setInfoPointerAsOf('');
    infoZoomEndRef.current = infoCandleDates.length
      ? infoCandleDates[infoCandleDates.length - 1]
      : '';
  }, [infoPayload, infoCandleDates]);

  const resolveInfoAxisDate = useCallback((params) => (
    resolveAxisPointerDate(params, infoCandleDates)
  ), [infoCandleDates]);

  const resolveInfoZoomDate = useCallback((params) => {
    const batch = Array.isArray(params?.batch) && params.batch.length
      ? params.batch[0]
      : params;
    if (!infoCandleDates.length) return '';
    const n = infoCandleDates.length;
    const endPct = Number(batch?.end);
    const pct = Number.isFinite(endPct) ? endPct : 100;
    const idx = Math.min(n - 1, Math.max(0, Math.round((pct / 100) * (n - 1))));
    return infoCandleDates[idx] || '';
  }, [infoCandleDates]);

  const infoChartEvents = useMemo(() => ({
    updateAxisPointer: (params) => {
      const d = resolveInfoAxisDate(params);
      if (d) setInfoPointerAsOf(d);
    },
    datazoom: (params) => {
      const d = resolveInfoZoomDate(params);
      if (d) infoZoomEndRef.current = d;
      setInfoPointerAsOf('');
    },
    globalout: () => setInfoPointerAsOf(''),
  }), [resolveInfoAxisDate, resolveInfoZoomDate]);

  const holdingDetail = holdings.find((row) => row.id === holdingDetailId) || null;
  if (holdingDetail) holdingDetailCacheRef.current = holdingDetail;
  const holdingDialogRow = holdingDetail || holdingDetailCacheRef.current;

  const closeInvestDialog = useCallback(() => {
    setInvestRow(null);
    setInvestShares('');
    setInvestNote('');
    setInvestError('');
    setInvestBusy(false);
  }, []);

  const openInvestDialog = (row) => {
    if (!row || row.held) return;
    const picked = Number(picks[row.id] || 0);
    setInvestRow({ ...row, pickedShares: picked });
    setInvestShares(picked > 0 ? String(picked) : '');
    setInvestNote(String(pickNotes[row.id] || ''));
    setInvestError('');
  };

  const submitInvest = async ({ shares, note, clear = false } = {}) => {
    const row = investRow;
    if (!row || !strategyKey || !snapshot?.dmId) return;
    const { minLot, lotStep } = lotRule(row);
    let clearing = Boolean(clear);
    if (!clearing) {
      const result = validateShareDraft(shares, minLot, lotStep);
      if (!result.ok) {
        setInvestError(result.message);
        showToast({ status: 'warning', content: result.message });
        return;
      }
      if (result.shares <= 0) {
        clearing = true;
      } else {
        const occupying = Number(picks[row.id] || 0) > 0;
        if (!occupying && remainingSlots <= 0) {
          setInvestError('已达组合上限');
          showToast({ status: 'warning', content: '已达组合上限' });
          return;
        }
      }
    }
    setInvestBusy(true);
    try {
      const snap = await pickDecisionShares(strategyKey, snapshot.dmId, {
        localId: row.id,
        shares: clearing ? 0 : Number(shares) || 0,
        note: clearing ? '' : String(note ?? ''),
      });
      applyLive(snap, undefined, { keepPicks: false });
      closeInvestDialog();
    } catch (err) {
      const message = errorMessage(err, '无法下单');
      setInvestError(message);
      showToast({ status: 'error', content: message });
      setInvestBusy(false);
    }
  };

  const openInfo = async (row) => {
    setInfoOpp(row);
    setInfoPayload(null);
    setInfoPointerAsOf('');
    if (!strategyKey || !snapshot?.dmId || !row) return;
    setInfoLoading(true);
    try {
      const buyDate = String(row.buyDate || row.heldBuyDate || '').trim();
      const payload = await fetchDecisionInfo(strategyKey, snapshot.dmId, {
        target: String(row.ticker || row.id || ''),
        // 持仓买入日可能早于默认 60 根窗口；拉满上限保证止盈/止损基准与买入钉同在图上
        n: buyDate ? 252 : undefined,
        buyDate: buyDate || undefined,
      });
      setInfoPayload(payload);
    } catch (err) {
      showToast({ status: 'error', content: errorMessage(err, '无法加载数据') });
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
            <StockStatusChips
              {...resolveLiveStatus(grid.row.ticker, liveStatusById, statusLoading)}
            />
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
        '该标的在当前日之前已经完成的机会盘点记录胜率（exit_date < 当天）。无样本为 —。',
      ),
    },
    {
      field: 'roi',
      width: 108,
      renderHeader: headerWithTooltip(
        '模拟 ROI',
        '该标的在当前日之前已经完成的机会盘点记录平均 ROI。无样本为 —。',
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
        />
      ),
    },
    {
      field: 'shares',
      headerName: '投资',
      width: 196,
      minWidth: 176,
      sortable: false,
      renderCell: (grid) => {
        if (grid.row.held) {
          return <Tag size="sm" status="neutral" variant="outline">已持有</Tag>;
        }
        return (
          <InvestOpenCell
            disabled={slotLocked(grid.row)}
            shares={picks[grid.row.id]}
            note={pickNotes[grid.row.id]}
            onOpen={() => openInvestDialog(grid.row)}
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
      showToast({ status: 'error', content: errorMessage(err, '无法返回查看') });
    });
  }, [resumePicking, snapshot?.phase]);

  const runAdvance = async () => {
    if (!strategyKey || !snapshot?.dmId || completed || advancing) return;
    if (billExceedsCash) {
      showToast({
        status: 'warning',
        content: `现金不足，可用 ${formatMoney(cashOnHand)} 元，本单约 ${formatMoney(billTotal)} 元`,
      });
      return;
    }
    closeCalendar();
    try {
      if (snapshot.phase !== 'confirming') {
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
      showToast({
        status: nextSnap.completed ? 'success' : 'info',
        content: nextSnap.completed ? '本次模拟回测已走完' : '已提交当天，停在下一事件日',
      });
    } catch (err) {
      setClockMotion('is-landed');
      setAdvancing(false);
      try {
        await resumePicking();
      } catch {
        /* 返回可改状态失败时仍提示推进错误 */
      }
      showToast({ status: 'error', content: errorMessage(err, '推进失败') });
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
      if (infoOpp || holdingDetailId || investRow || calendarAction) return;
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
  }, [advancing, calendarAction, completed, confirmOpen, hasOpps, holdingDetailId, infoOpp, investRow]);

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
        breadcrumbsCurrent="模拟回测"
        bannerTitle="决策模拟回测"
        bannerDescription="正在打开本次模拟回测。"
      >
        <Loading variant="inline" message="正在加载模拟回测…" className="is-block" />
      </PageLayout>
    );
  }

  if (loadError || !snapshot) {
    if (embedded) {
      return render({
        loading: false,
        error: loadError || '模拟回测不存在',
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
        breadcrumbsCurrent="模拟回测"
        bannerTitle="决策模拟回测"
        bannerDescription="无法打开本次模拟回测。"
        bannerRightSlot={(
          <Button component={RouterLink} to={designHref} variant="outlined" size="small">
            返回制定策略
          </Button>
        )}
      >
        <Message status="error">{loadError || '模拟回测不存在'}</Message>
      </PageLayout>
    );
  }

  const asof = snapshot.asof;
  const strategyWin = asof?.winRateLabel || '—';
  const strategyRoi = asof?.avgRoiLabel || '—';
  const rangeLabel = rangeStart && rangeEnd ? `${rangeStart} → ${rangeEnd}` : '—';

  const clockHud = (
    <div className={`decision-hud${embedded ? ' decision-hud--embedded' : ''}`} aria-label="模拟回测时钟">
      <div className="decision-hud-main">
        <div className="decision-calendar-block" data-ntq-help="decision-clock">
          <h2 className="decision-calendar-title">
            交易日历
          </h2>
          <div className={`decision-clock ${clockMotion}`}>
            <span className="decision-clock__date">{shownClockDate || '—'}</span>
            <span className="decision-clock__weekday">{weekdayLabel(shownClockDate)}</span>
          </div>
        </div>

        <div className="decision-hud-actions" data-ntq-help="decision-advance">
          {completed && typeof onViewReport === 'function' ? (
            <Button className="decision-advance-btn" variant="primary" onClick={onViewReport}>
              查看报告
            </Button>
          ) : (
            <Button className="decision-advance-btn" variant="primary" disabled={completed || advancing} onClick={requestAdvance} title="空格也可推进" aria-keyshortcuts="Space" icon="play" iconPlacement="start">
              {advancing ? '推进中' : '下一个事件（空格键）'}
            </Button>
          )}
          <Button variant="glass" className="decision-calendar-toggle" aria-haspopup="dialog" aria-expanded={calendarOpen} onClick={openCalendar}>
            事件回溯
          </Button>
        </div>

        <div className="decision-hud-metrics" data-ntq-help="decision-metrics">
          <div className="decision-hud-metric">
            <span className="ntq-caption ntq-muted">账户价值</span>
            <div className="decision-hud-metric__value ntq-decision-metric-value">
              {formatMoney(equity)}
              {showEquityDelta ? (
                <span className={`decision-hud-delta ${equityDelta >= 0 ? 'is-up' : 'is-down'}`}>
                  （{formatSignedMoney(equityDelta)}）
                </span>
              ) : null}
            </div>
          </div>
          <div className="decision-hud-metric">
            <span className="ntq-caption ntq-muted">可用资金</span>
            <div className="decision-hud-metric__value ntq-decision-metric-value">
              {formatMoney(snapshot.cash)}
              <span className="decision-hud-ratio">
                {' '}
                ({formatPct(cashRatio)})
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="decision-progress">
        <div className="decision-progress__track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(sessionPct)} aria-label="回测进度">
          <div className="decision-progress__fill" style={{ width: `${sessionPct}%` }} />
        </div>
        <span className="decision-progress__label ntq-caption">
          {totalDays > 0
            ? `已走 ${elapsedDays} / ${totalDays} 个交易日`
            : (shownClockDate ? `停在 ${shownClockDate}` : '区间未知')}
        </span>
      </div>
    </div>
  );

  const playInner = (
    <>
      {completed ? (
        <Message status="warning">
          本次模拟回测已走完，只读回看。不能改股数，也不能再推进。
        </Message>
      ) : null}

      {embedded ? null : (
      <div className="decision-hud-card decision-card">
        <div className="decision-card__content">
          {clockHud}
        </div>
      </div>
      )}

      <Dialog
        open={calendarOpen}
        onClose={closeCalendar}
        maxWidth={false}
        fullWidth={false}
        scroll="paper"
        PaperProps={{ className: 'decision-month-popover' }}
      >
        <div className="decision-month">
          <div className="decision-month-nav">
            <Button aria-label="上个月" disabled={!canPrevMonth} onClick={() => {
                const next = shiftMonth(viewYear, viewMonth, -1);
                setViewYear(next.year);
                setViewMonth(next.month);
              }} variant="ghost" icon="arrowBack" />
            <span className="decision-month-title">{monthTitle(viewYear, viewMonth)}</span>
            <Button aria-label="下个月" disabled={!canNextMonth} onClick={() => {
                const next = shiftMonth(viewYear, viewMonth, 1);
                setViewYear(next.year);
                setViewMonth(next.month);
              }} variant="ghost" icon="chevronRight" />
          </div>
          {calendarOpen ? (
            <MonthGrid
              year={viewYear}
              month={viewMonth}
              clockDate={clockDate}
              days={calendarDays}
              rangeStart={rangeStart}
              rangeEnd={rangeEnd}
              onActionClick={setCalendarAction}
            />
          ) : null}
          <span className="decision-month-legend ntq-caption">
            <span className="decision-month-legend__now">当前停顿日</span>
            <span className="decision-month-legend__opp">发现机会</span>
            <span className="decision-month-legend__buy">买入</span>
            <span className="decision-month-legend__sell">卖出</span>
            未来日期不标注 · 不能点选跳转
          </span>
        </div>
      </Dialog>

      <div className={`decision-play-split ${advancing ? 'is-advancing' : ''}`}>
        <div className="decision-left">
          <div className="decision-card">
            <div className="decision-aside decision-card__content">
              {hideStrategyMeta ? null : (
              <div className="decision-aside-section">
                <span className="decision-aside-title ntq-decision-subtitle ntq-decision-strong">
                  策略与模拟
                </span>
                <DefinitionList
                  items={[
                    { label: '策略', value: snapshot.strategyKey || strategyKey },
                    { label: '版本', value: snapshot.versionId || '—' },
                    { label: '模拟回测', value: String(snapshot.dmId) },
                    { label: '回测区间', value: rangeLabel },
                    { label: '最大同时持有数', value: String(snapshot.maxPortfolioSize || '—') },
                  ]}
                />
              </div>
              )}

              <div className="decision-aside-section" data-ntq-help="decision-holdings">
                <span className="decision-aside-title ntq-decision-subtitle ntq-decision-strong">
                  持仓状态
                </span>
                <DefinitionList
                  items={[
                    { label: '持仓市值', value: formatMoney(holdingsValue) },
                  ]}
                />
                {holdings.length ? (
                  <>
                    <div className="decision-holding-head">
                      <span>股票</span>
                      <span>持有</span>
                      <span>盈亏</span>
                    </div>
                    <div className="decision-holding-list">
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
                              <StockStatusChips
                                {...resolveLiveStatus(row.ticker, liveStatusById, statusLoading)}
                              />
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
                    </div>
                    <span className="decision-holding-hint ntq-caption ntq-muted">
                      点一行查看明细
                    </span>
                  </>
                ) : (
                  <span className="ntq-muted">当前无持仓</span>
                )}
              </div>

              <div className="decision-aside-section">
                <button
                  type="button"
                  className={`decision-aside-fold${positionOpen ? ' is-open' : ''}`}
                  aria-expanded={positionOpen}
                  onClick={() => setPositionOpen((open) => !open)}
                >
                  <span className="decision-aside-title ntq-decision-subtitle ntq-decision-strong">
                    持仓约束与策略统计
                  </span>
                  <Icon name="expandMore" size="sm" />
                </button>
                {positionOpen ? (
                  <DefinitionList
                    items={[
                      { label: '持仓 / 上限', value: `${snapshot.openPositionCount} / ${snapshot.maxPortfolioSize || '—'}` },
                      { label: '至今最大回撤', value: formatDrawdown(null) },
                      { label: '策略至今胜率', value: strategyWin },
                      { label: '策略平均回报率', value: strategyRoi },
                    ]}
                  />
                ) : null}
              </div>
            </div>
          </div>
        </div>

        <div className="decision-right">
          <div data-ntq-help="decision-events" className="decision-card">
            <div className="decision-card__content">
              <span className="ntq-decision-subtitle ntq-decision-strong">今日事件</span>
              {events.length ? (
                <div className="ntq-decision-stack">
                  {events.map((row) => (
                    <div key={`${row.date}-${row.ticker}-${row.shares}`} className={`decision-event ${row.win ? 'is-win' : 'is-loss'}`}>
                      <span className="ntq-caption ntq-muted">{row.date}</span>
                      <span>{row.text}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="ntq-muted">
                  今日无出场结算。
                </span>
              )}
            </div>
          </div>

          <div className={[hasOpps ? 'decision-opp-card is-hot' : 'decision-opp-card', "decision-card"].filter(Boolean).join(" ")} data-ntq-help="decision-opps">
            <div className="decision-card__content">
              <div className="decision-opp-head">
                <h2 className={`decision-opp-title ${hasOpps ? 'is-hot' : 'is-empty'}`}>
                  {hasOpps ? '发现了新的可交易机会' : '今日没有可交易的机会'}
                </h2>
                {hasOpps ? (
                  <span className="decision-opp-meta">
                    点击股票名称查看当前状态。还可选择
                    {' '}
                    <span className="decision-opp-slots">{remainingSlots}</span>
                    {' '}
                    个机会
                    {remainingSlots <= 0 ? (
                      <span className="decision-opp-slots-full">（已达组合上限）</span>
                    ) : null}
                  </span>
                ) : null}
              </div>
              {hasOpps ? (
                <DataGrid
                  autoHeight
                  bordered={false}
                  className="decision-opp-grid"
                  rows={oppRows}
                  columns={oppColumns}
                  hideFooter
                  disableRowSelectionOnClick
                  onCellClick={(params, event) => {
                    if (event.target.closest('.decision-invest-cell, .decision-invest-open')) {
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
                />
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <HoldingDetailDialog
        open={Boolean(holdingDetail)}
        row={holdingDialogRow}
        equity={equity}
        statusTags={resolveLiveStatus(
          holdingDialogRow?.ticker,
          liveStatusById,
          statusLoading,
        ).tags}
        statusLoading={resolveLiveStatus(
          holdingDialogRow?.ticker,
          liveStatusById,
          statusLoading,
        ).loading}
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
            buyPrice: row.buyPrice,
            goals: row.goals,
          });
        } : undefined}
      />

      <InvestDialog
        open={Boolean(investRow)}
        row={investRow}
        shares={investShares}
        note={investNote}
        error={investError}
        submitting={investBusy}
        onSharesChange={(value) => {
          setInvestShares(value);
          setInvestError('');
        }}
        onNoteChange={(value) => setInvestNote(String(value || '').slice(0, NOTE_MAX))}
        onStep={(direction) => {
          if (!investRow) return;
          const { minLot, lotStep } = lotRule(investRow);
          const next = stepShares(investShares, direction, minLot, lotStep);
          setInvestShares(next > 0 ? String(next) : '');
          setInvestError('');
        }}
        onApplySuggested={() => {
          const shares = Number(investRow?.suggestedShares) || 0;
          if (shares > 0) {
            setInvestShares(String(shares));
            setInvestError('');
          }
        }}
        onClear={() => submitInvest({ clear: true })}
        onCancel={closeInvestDialog}
        onConfirm={() => submitInvest({ shares: investShares, note: investNote })}
      />

      <CalendarActionDialog
        open={Boolean(calendarAction)}
        action={calendarAction}
        onClose={() => setCalendarAction(null)}
      />

      <Dialog
        open={confirmOpen}
        onClose={cancelConfirm}
        title="确认当天选择"
        size="sm"
        actions={(
          <>
            <Button variant="ghost" onClick={cancelConfirm}>返回查看</Button>
            <Button
              variant="primary"
              onClick={runAdvance}
              disabled={advancing || billExceedsCash}
            >
              确认推进（空格键）
            </Button>
          </>
        )}
      >
        <p className="ntq-muted">
          提交后不可改当日选择。空选择等于本日不买。空格确认后，日历会按交易日走到下一事件。
        </p>
        {bill.length ? (
          bill.map((row) => (
            <div key={row.id} className="ntq-decision-stack ntq-decision-stack--row">
              <div className="decision-stock-with-status">
                [{row.id}] {row.name}{' '}
                <StockStatusChips
                  {...resolveLiveStatus(row.ticker, liveStatusById, statusLoading)}
                />{' '}
                {row.shares.toLocaleString()} 股
                {row.note ? (
                  <span className="decision-bill-note"> · {row.note}</span>
                ) : null}
              </div>
              <span>约 {formatMoney(row.notional)}</span>
            </div>
          ))
        ) : (
          <span>当前选择：（空，本日不买）</span>
        )}
        <div className="ntq-decision-stack ntq-decision-stack--row ntq-decision-stack--ruled">
          <span className="ntq-muted">可用资金</span>
          <span>{formatMoney(cashOnHand)} 元</span>
        </div>
        <div className="ntq-decision-stack ntq-decision-stack--row">
          <span className="ntq-decision-strong">合计（约）</span>
          <span className="ntq-decision-strong">
            {formatMoney(billTotal)} 元
          </span>
        </div>
        {billExceedsCash ? (
          <Message status="warning">
            这几笔加起来超过可用资金。返回查看后减少买入，或卖掉持仓后再买。
          </Message>
        ) : null}
      </Dialog>

      <Dialog
        open={Boolean(infoOpp)}
        onClose={() => {
          setInfoOpp(null);
          setInfoPointerAsOf('');
        }}
        fullScreen
        className="decision-info-chart-dialog"
        title={(
          <span className="decision-info-dialog-title">
            <span className="decision-stock-with-status">
              {infoOpp ? opportunityStockLabel(infoOpp) : '市场数据'}
              {infoOpp ? (
                <StockStatusChips
                  {...resolveLiveStatus(
                    infoOpp.ticker || infoPayload?.entityId,
                    liveStatusById,
                    statusLoading,
                  )}
                />
              ) : null}
              <span className="ntq-caption ntq-muted decision-info-title-hint">
                查看 K 线
              </span>
            </span>
            <Button
              variant="ghost"
              icon="cancel"
              aria-label="关闭"
              onClick={() => {
                setInfoOpp(null);
                setInfoPointerAsOf('');
              }}
            />
          </span>
        )}
      >
        {infoOpp ? (
          <div className="ntq-decision-stack ntq-decision-stack--gap-md ntq-decision-stack--min0">
            <span className="ntq-muted">
              截至 {clockDate} · 前复权数据停在当前日，不含未来
              {(() => {
                const panels = new Set(
                  (infoPayload?.indicatorSeries || [])
                    .map((row) => row.panel)
                    .filter((p) => p && p !== 'overlay'),
                );
                const names = [];
                if (panels.has('macd')) names.push('MACD');
                if (panels.has('oscillator')) names.push('振荡指标');
                const layerNames = (infoPayload?.chartLayers || [])
                  .map((l) => l.label || l.role)
                  .filter(Boolean);
                if (names.length) return ` · 副图：${names.join(' / ')}`;
                if (layerNames.length) return ` · 分层：${layerNames.join(' · ')}`;
                return '';
              })()}
            </span>
            <div className="ntq-decision-stack ntq-decision-stack--gap-sm">
              <div className="ntq-decision-stack ntq-decision-stack--row">
                <span className="ntq-muted">策略截至当日</span>
                <span>
                  胜率 {strategyWin}  平均ROI {strategyRoi}
                  {asof?.sampleSize != null ? `  n=${asof.sampleSize}` : ''}
                </span>
              </div>
              <div className="ntq-decision-stack ntq-decision-stack--row">
                <span className="ntq-muted">本标的截至当日</span>
                <span>
                  胜率 {infoPayload?.tickerStats?.winRateLabel || infoOpp.wr}
                  {' '}
                  平均ROI {infoPayload?.tickerStats?.avgRoiLabel || infoOpp.roi}
                </span>
              </div>
            </div>
            {infoLoading ? (
              <Loading variant="inline" message="正在加载市场数据…" className="is-block" />
            ) : (
              <div className="ntq-decision-stack ntq-decision-stack--gap-md ntq-decision-stack--grow ntq-decision-stack--min0">
                <div>
                  <ChartPanel
                    title=""
                    option={infoChart}
                    height={infoChartHeight}
                    framed={false}
                    onEvents={infoChartEvents}
                    note={infoPayload?.candles?.length
                      ? '主图：K线（前复权）与策略声明指标 / 分层数据。悬停查看财报 PIT。使用底部滑块调整可见区间。'
                      : '没有截至当前日的市场数据。'}
                  />
                </div>
                <FinancePitCard
                  visible={infoHasFinanceLayer}
                  live={infoFinanceLive}
                  pointerAsOf={infoPointerAsOf}
                  snapshot={infoFinanceSnapshot}
                />
              </div>
            )}
          </div>
        ) : null}
      </Dialog>
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
      breadcrumbsCurrent={`模拟回测 #${snapshot.dmId}`}
      bannerTitle={`决策模拟回测 · #${snapshot.dmId}`}
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
