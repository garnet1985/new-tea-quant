import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
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
  Popover,
  Snackbar,
  Stack,
  TextField,
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
  decisionLobbyPath,
  doneDecisionDay,
    fetchDecisionHoldings,
    fetchDecisionInfo,
    fetchDecisionSession,
    holdingsMarketValue,
    nextDecisionDay,
    pickDecisionShares,
    resetDecisionDraft,
} from '../../api/decisionApi';
import { isHttpStatusError } from 'services/request';
import {
  buildMonthCells,
  canShiftMonth,
  collectEventMarks,
  countTradingDaysInclusive,
  dateToYearMonth,
  formatMoney,
  formatPct,
  formatSignedMoney,
  mapStockStatusTags,
  monthTitle,
  shiftMonth,
  weekdayLabel,
} from './decisionFormat';
import './decisionPage.scss';

const WEEKDAY_HEADS = ['一', '二', '三', '四', '五', '六', '日'];

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

function markTooltip(mark) {
  if (!mark) return '';
  const bits = [];
  if (mark.exit) bits.push('出场');
  if (mark.opp) bits.push('新机会');
  return bits.join(' · ');
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

function validateShareDraft(raw, lotSize) {
  const text = String(raw ?? '').trim();
  if (!text) return { ok: true, shares: 0 };
  if (!/^\d+$/.test(text)) return { ok: false, message: '须为非负整数' };
  const shares = Number(text);
  if (!Number.isFinite(shares) || shares < 0) return { ok: false, message: '须为非负整数' };
  if (shares > 0 && lotSize && shares % Number(lotSize) !== 0) {
    return { ok: false, message: `须为 ${lotSize} 的整数倍` };
  }
  return { ok: true, shares };
}

function headerWithTooltip(label, title) {
  return () => (
    <Tooltip title={title}>
      <span className="decision-col-help">{label}</span>
    </Tooltip>
  );
}

function SharesInvestCell({
  open,
  disabled,
  draft,
  error,
  lotSize,
  ticker,
  onOpen,
  onDraftChange,
  onCommit,
  onCancel,
}) {
  if (!open) {
    return (
      <Button
        size="small"
        variant="outlined"
        disabled={disabled}
        onClick={(event) => {
          event.stopPropagation();
          onOpen();
        }}
      >
        投资
      </Button>
    );
  }
  return (
    <TextField
      className="decision-shares-input"
      size="small"
      autoFocus
      disabled={disabled}
      value={draft}
      error={Boolean(error)}
      placeholder={lotSize ? `${lotSize} 的整数倍` : '股数'}
      inputProps={{ inputMode: 'numeric', 'aria-label': `股数 ${ticker}` }}
      onClick={(event) => event.stopPropagation()}
      onMouseDown={(event) => event.stopPropagation()}
      onChange={(event) => onDraftChange(event.target.value)}
      onBlur={(event) => onCommit(event.target.value)}
      onKeyDown={(event) => {
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
  );
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
    ['持有时长', `${Number(row.holdDays) || 0} 日`],
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
          仍持有时目标都未触发。触发即整笔出场，不会留在持仓列表里。
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

function MonthGrid({ year, month, clockDate, marks, rangeStart, rangeEnd }) {
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
        const mark = !outOfRange && !future ? marks[date] : null;
        const cell = (
          <Box
            className={[
              'decision-month-cell',
              date === clockDate ? 'is-now' : '',
              outOfRange ? 'is-out' : '',
              future ? 'is-future' : '',
              mark?.exit ? 'has-exit' : '',
              mark?.opp ? 'has-opp' : '',
            ].filter(Boolean).join(' ')}
          >
            <span className="decision-month-cell__num">{Number(date.slice(8))}</span>
            <span className="decision-month-cell__dots" aria-hidden>
              {mark?.exit ? <i className="is-exit" /> : null}
              {mark?.opp ? <i className="is-opp" /> : null}
            </span>
          </Box>
        );
        const tip = markTooltip(mark);
        return tip ? (
          <Tooltip key={date} title={tip} placement="top">
            {cell}
          </Tooltip>
        ) : (
          <React.Fragment key={date}>{cell}</React.Fragment>
        );
      })}
    </Box>
  );
}

function DecisionPlayPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const strategyKey = String(params.get('strategy') || '').trim();
  const readonlyQuery = params.get('readonly') === '1';
  const sessionId = String(params.get('session') || '').trim();

  const [snapshot, setSnapshot] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [picks, setPicks] = useState({});
  const [events, setEvents] = useState([]);
  const [historyDays, setHistoryDays] = useState([]);
  const [equityDelta, setEquityDelta] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [pageReady, setPageReady] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [holdingDetailId, setHoldingDetailId] = useState(null);
  const [infoOpp, setInfoOpp] = useState(null);
  const [infoPayload, setInfoPayload] = useState(null);
  const [infoLoading, setInfoLoading] = useState(false);
  const [shareEditors, setShareEditors] = useState({});
  const [toast, setToast] = useState('');
  const [advancing, setAdvancing] = useState(false);
  const [calendarAnchor, setCalendarAnchor] = useState(null);
  const [viewYear, setViewYear] = useState(() => dateToYearMonth('').year);
  const [viewMonth, setViewMonth] = useState(() => dateToYearMonth('').month);
  const animRef = useRef({ cancelled: false, timer: null });
  const pickTimerRef = useRef(null);
  const pendingPicksRef = useRef({});
  const equityRef = useRef(null);
  const holdingDetailCacheRef = useRef(null);
  const calendarOpen = Boolean(calendarAnchor);
  const lobbyHref = decisionLobbyPath(strategyKey);

  const rememberHistory = useCallback((snap, hopEvents) => {
    if (!snap?.clockDate) return;
    setHistoryDays((prev) => {
      const existing = prev.find((row) => row.date === snap.clockDate);
      const rest = prev.filter((row) => row.date !== snap.clockDate);
      return [...rest, {
        date: snap.clockDate,
        opps: snap.opps || [],
        events: hopEvents !== undefined ? hopEvents : (existing?.events || []),
      }];
    });
  }, []);

  const applyLive = useCallback((snap, nextHoldings, { hopEvents, keepPicks = false } = {}) => {
    setSnapshot(snap);
    if (Array.isArray(nextHoldings)) setHoldings(nextHoldings);
    if (!keepPicks) {
      setPicks(snap.picks || {});
      setShareEditors({});
    }
    if (hopEvents !== undefined) setEvents(hopEvents);
    rememberHistory(snap, hopEvents);
    const month = dateToYearMonth(snap.clockDate);
    if (snap.clockDate) {
      setViewYear(month.year);
      setViewMonth(month.month);
    }
  }, [rememberHistory]);

  const loadHoldings = useCallback(async (dmId) => {
    if (!strategyKey || !dmId) return [];
    try {
      return await fetchDecisionHoldings(strategyKey, dmId);
    } catch {
      return [];
    }
  }, [strategyKey]);

  useEffect(() => {
    animRef.current.cancelled = false;
    if (!strategyKey || !sessionId) {
      navigate(strategyKey ? lobbyHref : '/decision', { replace: true });
      return undefined;
    }

    let cancelled = false;
    (async () => {
      setPageReady(false);
      setLoadError('');
      setEvents([]);
      setHistoryDays([]);
      setEquityDelta(null);
      equityRef.current = null;
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
      animRef.current.cancelled = true;
      if (animRef.current.timer) window.clearTimeout(animRef.current.timer);
      if (pickTimerRef.current) window.clearTimeout(pickTimerRef.current);
    };
  }, [strategyKey, sessionId, navigate, lobbyHref, applyLive, loadHoldings]);

  const clockDate = snapshot?.clockDate || '';
  const completed = Boolean(snapshot?.completed || readonlyQuery);
  const rangeStart = snapshot?.startDate || '';
  const rangeEnd = snapshot?.endDate || '';
  const holdingsValue = holdingsMarketValue(holdings);
  const equity = (Number(snapshot?.cash) || 0) + holdingsValue;
  const cashRatio = equity > 0 ? (Number(snapshot?.cash) || 0) / equity : null;
  const hasOpps = Boolean(snapshot?.hasOpps);
  const selectableSlots = Math.max(
    0,
    (Number(snapshot?.maxPortfolioSize) || 0) - (Number(snapshot?.openPositionCount) || 0),
  );
  const showEquityDelta = typeof equityDelta === 'number' && equityDelta !== 0;

  useEffect(() => {
    if (snapshot) equityRef.current = equity;
  }, [snapshot, equity]);

  const eventMarks = useMemo(
    () => (calendarOpen ? collectEventMarks(historyDays, clockDate) : {}),
    [calendarOpen, historyDays, clockDate],
  );
  const elapsedDays = useMemo(
    () => countTradingDaysInclusive(rangeStart, clockDate),
    [rangeStart, clockDate],
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
    return buildStockKlineChartOptionFromPayload({
      candles: infoPayload.candles,
      indicator_series: infoPayload.indicatorSeries || [],
      markers: clockDate ? [{
        type: 'opportunity',
        date: clockDate.replace(/-/g, ''),
        label: '当前日',
      }] : [],
    });
  }, [infoPayload, clockDate]);

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
    if (last && last !== snapshot) applyLive(last, undefined, { keepPicks: true });
  }, [applyLive, snapshot, strategyKey]);

  const schedulePick = (localId, shares) => {
    pendingPicksRef.current[localId] = shares;
    if (pickTimerRef.current) window.clearTimeout(pickTimerRef.current);
    pickTimerRef.current = window.setTimeout(() => {
      flushPicks().catch((err) => {
        const message = errorMessage(err, '无法写入股数');
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

  const openShareEditor = (row, preset) => {
    if (row.held) return;
    const current = Number(picks[row.id] || 0);
    const draft = preset != null ? String(preset) : (current > 0 ? String(current) : '');
    setShareEditors((prev) => ({
      ...prev,
      [row.id]: { open: true, draft, error: '' },
    }));
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
    const raw = rawValue != null ? rawValue : (editor?.draft ?? (picks[row.id] != null ? String(picks[row.id]) : ''));
    const result = validateShareDraft(raw, row.lotSize);
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
    setShareEditors((prev) => ({
      ...prev,
      [row.id]: { open: true, draft: String(result.shares), error: '' },
    }));
    setPicks((prev) => ({ ...prev, [row.id]: result.shares }));
    schedulePick(row.id, result.shares);
  };

  const cancelShareEditor = (row) => {
    const current = Number(picks[row.id] || 0);
    if (current > 0) {
      setShareEditors((prev) => ({
        ...prev,
        [row.id]: { open: true, draft: String(current), error: '' },
      }));
      return;
    }
    setShareEditors((prev) => {
      const next = { ...prev };
      delete next[row.id];
      return next;
    });
  };

  const applySuggestedShares = (row) => {
    if (row.held || row.suggestedShares == null || row.suggestedShares <= 0) return;
    setShareEditors((prev) => ({
      ...prev,
      [row.id]: { open: true, draft: String(row.suggestedShares), error: '' },
    }));
    setPicks((prev) => ({ ...prev, [row.id]: row.suggestedShares }));
    schedulePick(row.id, row.suggestedShares);
  };

  const shareDisabled = completed || advancing || snapshot?.phase === 'confirming';
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
            <span className="decision-opp-stock">{opportunityStockLabel(grid.row)}</span>
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
        '目前为止的模拟回测胜率（该标的 as-of；无样本为 —）',
      ),
    },
    {
      field: 'roi',
      width: 108,
      renderHeader: headerWithTooltip(
        '模拟 ROI',
        '目前为止的模拟回测平均回报率（ROI，该标的 as-of；无样本为 —）',
      ),
    },
    {
      field: 'suggestedShares',
      width: 112,
      sortable: false,
      renderHeader: headerWithTooltip(
        '建议买入',
        '凯莉公式建议股数：当前现金 × as-of 胜率，再乘策略凯莉折扣，并按手数取整。无样本为 —；未扣其他草稿。',
      ),
      renderCell: (grid) => {
        const suggested = grid.row.suggestedShares;
        if (suggested == null || grid.row.held) return '—';
        if (suggested <= 0 || shareDisabled) {
          return <span>{Number(suggested).toLocaleString()}</span>;
        }
        return (
          <Button
            size="small"
            variant="text"
            onClick={(event) => {
              event.stopPropagation();
              applySuggestedShares(grid.row);
            }}
          >
            {Number(suggested).toLocaleString()}
          </Button>
        );
      },
    },
    {
      field: 'shares',
      headerName: '投资',
      width: 132,
      sortable: false,
      renderCell: (grid) => {
        if (grid.row.held) {
          return <Chip size="small" variant="outlined" label="已持有" />;
        }
        const editor = shareEditors[grid.row.id];
        const picked = Number(picks[grid.row.id] || 0);
        const open = Boolean(editor?.open) || picked > 0;
        const draft = editor?.draft ?? (picked > 0 ? String(picked) : '');
        return (
          <SharesInvestCell
            open={open}
            disabled={shareDisabled}
            draft={draft}
            error={editor?.error || ''}
            lotSize={grid.row.lotSize}
            ticker={grid.row.ticker}
            onOpen={() => openShareEditor(grid.row)}
            onDraftChange={(value) => updateShareDraft(grid.row.id, value)}
            onCommit={(raw) => commitShareEditor(grid.row, raw)}
            onCancel={() => cancelShareEditor(grid.row)}
          />
        );
      },
    },
  ];

  const sleep = (ms) => new Promise((resolve) => {
    animRef.current.timer = window.setTimeout(resolve, ms);
  });

  const openCalendar = (event) => {
    if (calendarAnchor) {
      setCalendarAnchor(null);
      return;
    }
    const month = dateToYearMonth(clockDate);
    setViewYear(month.year);
    setViewMonth(month.month);
    setCalendarAnchor(event.currentTarget);
  };

  const closeCalendar = (event) => {
    if (event?.currentTarget?.closest?.('.decision-calendar-toggle')) return;
    if (event?.target?.closest?.('.decision-calendar-toggle')) return;
    setCalendarAnchor(null);
  };

  const runAdvance = async () => {
    if (!strategyKey || !snapshot?.dmId || completed) return;
    setConfirmOpen(false);
    closeCalendar();
    const prevEquity = equityRef.current;
    try {
      if (snapshot.phase !== 'confirming') {
        await flushPicks();
        const confirming = await doneDecisionDay(strategyKey, snapshot.dmId);
        applyLive(confirming, undefined, { keepPicks: true });
      }
      if (!prefersReducedMotion()) {
        setAdvancing(true);
        await sleep(280);
        if (animRef.current.cancelled) return;
      }
      const nextSnap = await nextDecisionDay(strategyKey, snapshot.dmId);
      const held = await loadHoldings(nextSnap.dmId);
      const nextEquity = (Number(nextSnap.cash) || 0) + holdingsMarketValue(held);
      applyLive(nextSnap, held, { hopEvents: nextSnap.events || [], keepPicks: false });
      if (typeof prevEquity === 'number') setEquityDelta(nextEquity - prevEquity);
      else setEquityDelta(null);
      setAdvancing(false);
      setToast(nextSnap.completed ? '本局已走完' : '已提交当天，停在下一事件日');
    } catch (err) {
      setAdvancing(false);
      setToast(errorMessage(err, '推进失败'));
    }
  };

  const resetDraft = async () => {
    if (!strategyKey || !snapshot?.dmId) return;
    try {
      pendingPicksRef.current = {};
      if (pickTimerRef.current) window.clearTimeout(pickTimerRef.current);
      const snap = await resetDecisionDraft(strategyKey, snapshot.dmId);
      applyLive(snap, undefined, { keepPicks: false });
      setConfirmOpen(false);
      setToast('已清空草稿，仍停在当天');
    } catch (err) {
      setToast(errorMessage(err, '无法清空草稿'));
    }
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

  if (!pageReady && !loadError) {
    return (
      <PageLayout
        className="decision-page"
        breadcrumbsItems={[{ label: '决策者', to: lobbyHref }]}
        breadcrumbsCurrent="对局"
        bannerTitle="决策者对局"
        bannerDescription="正在打开这一局。"
      >
        <InlineLoadingState block message="正在加载对局现场…" />
      </PageLayout>
    );
  }

  if (loadError || !snapshot) {
    return (
      <PageLayout
        className="decision-page"
        breadcrumbsItems={[{ label: '决策者', to: lobbyHref }]}
        breadcrumbsCurrent="对局"
        bannerTitle="决策者对局"
        bannerDescription="无法打开这一局。"
        bannerRightSlot={(
          <Button component={RouterLink} to={lobbyHref} variant="outlined" size="small">
            返回入口
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

  return (
    <PageLayout
      className="decision-page"
      breadcrumbsItems={[{ label: '决策者', to: lobbyHref }]}
      breadcrumbsCurrent={`第 ${snapshot.dmId} 局`}
      bannerTitle={`决策者对局 · 第 ${snapshot.dmId} 局`}
      bannerDescription="时钟只显示当前停顿日。推进后总进度前移；月历是只读地图，只标注已经发生的事件。"
      bannerRightSlot={(
        <Button component={RouterLink} to={lobbyHref} variant="outlined" size="small">
          返回入口
        </Button>
      )}
    >
      {completed ? (
        <Alert severity="warning" variant="outlined" sx={{ mb: 2 }}>
          本局已走完，只读回看。不能改股数，也不能再推进。
        </Alert>
      ) : null}

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent className="decision-hud" aria-label="对局时钟">
          <Box className="decision-hud-main">
            <Box className="decision-calendar-block">
              <Typography className="decision-calendar-title" component="h2">
                交易日历
              </Typography>
              <Box
                key={clockDate}
                className={`decision-clock ${advancing ? 'is-advancing' : 'is-landed'}`}
              >
                <Typography className="decision-clock__date">{clockDate || '—'}</Typography>
                <Typography className="decision-clock__weekday">{weekdayLabel(clockDate)}</Typography>
              </Box>
            </Box>

            <Box className="decision-hud-actions">
              <Button
                className="decision-advance-btn"
                variant="contained"
                disabled={completed || advancing}
                startIcon={<NtqIcon name="play" size={16} />}
                onClick={() => setConfirmOpen(true)}
              >
                {advancing ? '推进中' : '推进'}
              </Button>
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

            <Box className="decision-hud-metrics">
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
                : (clockDate ? `停在 ${clockDate}` : '区间未知')}
            </Typography>
          </Box>
        </CardContent>
      </Card>

      <Popover
        open={calendarOpen}
        anchorEl={calendarAnchor}
        onClose={closeCalendar}
        keepMounted={false}
        disableScrollLock
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
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
              marks={eventMarks}
              rangeStart={rangeStart}
              rangeEnd={rangeEnd}
            />
          ) : null}
          <Typography className="decision-month-legend" variant="caption">
            <span className="decision-month-legend__now">当前停顿日</span>
            <span className="decision-month-legend__opp">已出现的机会</span>
            <span className="decision-month-legend__exit">已发生的出场</span>
            未来日期不标注 · 不能点选跳转
          </Typography>
        </Box>
      </Popover>

      <Box className="decision-play-split">
        <Box className="decision-left">
          <Card variant="outlined">
            <CardContent className="decision-aside">
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

              <Box className="decision-aside-section">
                <Typography className="decision-aside-title" variant="subtitle1" fontWeight={700}>
                  仓位状态
                </Typography>
                {[
                  ['持仓 / 上限', `${snapshot.openPositionCount} / ${snapshot.maxPortfolioSize || '—'}`],
                  ['持仓市值', formatMoney(holdingsValue)],
                  ['至今最大回撤', formatDrawdown(null)],
                  ['策略至今胜率', strategyWin],
                  ['策略平均回报率', strategyRoi],
                ].map(([label, value]) => (
                  <Typography key={label} className="decision-kv" variant="body2">
                    <span className="decision-kv__label">{label}</span>
                    <span className="decision-kv__value">{value}</span>
                  </Typography>
                ))}
              </Box>

              <Box className="decision-aside-section">
                <Typography className="decision-aside-title" variant="subtitle1" fontWeight={700}>
                  持仓
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
            </CardContent>
          </Card>
        </Box>

        <Box className="decision-right">
          <Card variant="outlined">
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

          <Card variant="outlined" className={hasOpps ? 'decision-opp-card is-hot' : 'decision-opp-card'}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 1 }} spacing={2}>
                <Typography
                  className={`decision-opp-title ${hasOpps ? 'is-hot' : 'is-empty'}`}
                  component="h2"
                >
                  {hasOpps ? '发现了新的可交易机会' : '今日没有可交易的机会'}
                </Typography>
                {hasOpps ? (
                  <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0, pt: 0.75 }}>
                    点击查看股票当前状态。可选择机会数：{selectableSlots}
                  </Typography>
                ) : null}
              </Stack>
              {hasOpps ? (
                <DataGrid
                  autoHeight
                  rows={oppRows}
                  columns={oppColumns}
                  localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
                  hideFooter
                  disableRowSelectionOnClick
                  getRowClassName={(params) => (params.row.held ? 'is-held' : '')}
                  getRowHeight={(params) => {
                    const row = oppRows.find((item) => item.id === params.id);
                    return row?.held ? 64 : null;
                  }}
                  onRowClick={(gridParams, event) => {
                    if (event.target.closest('input, button, .MuiButton-root')) return;
                    openInfo(gridParams.row);
                  }}
                  sx={{
                    border: 0,
                    '& .MuiDataGrid-row': { cursor: 'pointer' },
                    '& .MuiDataGrid-row:hover': {
                      backgroundColor: 'rgba(34, 211, 238, 0.08)',
                    },
                    '& .MuiDataGrid-cell': { outline: 'none' },
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
          });
        } : undefined}
      />

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>确认当天选择</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            提交后不可改当日选择。空选择等于本日不买，进度条会带到下一事件日。
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
            <Typography fontWeight={700}>合计</Typography>
            <Typography fontWeight={700}>{formatMoney(billTotal)} 元</Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={resetDraft}>重新下单</Button>
          <Button variant="contained" onClick={runAdvance} disabled={advancing}>确认推进</Button>
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
                    ? '主图：K线（前复权）与策略声明指标。使用底部滑块调整可见区间。'
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
    </PageLayout>
  );
}

export default DecisionPlayPage;
