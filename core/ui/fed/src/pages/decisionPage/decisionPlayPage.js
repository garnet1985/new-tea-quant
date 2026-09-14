import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
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
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import { buildStockKlineChartOptionFromPayload } from '../strategyWorkbenchPage/panels/strategyReportPanel/lib/stockKlineChart';
import {
  BACKTEST_END,
  BACKTEST_START,
  DECISION_STRATEGY,
  SESSION_DAYS,
  buildMockCandles,
  buildMonthCells,
  canShiftMonth,
  collectEventMarks,
  countTradingDaysInclusive,
  dateToYearMonth,
  formatMoney,
  formatPct,
  formatSignedMoney,
  monthTitle,
  shiftMonth,
  weekdayLabel,
} from './mockDecisionData';
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

function markTooltip(mark) {
  if (!mark) return '';
  const bits = [];
  if (mark.exit) bits.push('出场');
  if (mark.opp) bits.push('新机会');
  return bits.join(' · ');
}

function MonthGrid({ year, month, clockDate, marks }) {
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
        const outOfRange = date < BACKTEST_START || date > BACKTEST_END;
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
  const [params] = useSearchParams();
  const isNew = params.get('new') === '1';
  const readonlyQuery = params.get('readonly') === '1';
  const sessionId = isNew ? 4 : Number(params.get('session') || 1);
  const days = SESSION_DAYS[sessionId] || SESSION_DAYS[1];

  const [dayIndex, setDayIndex] = useState(0);
  const [picks, setPicks] = useState({});
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [infoOpp, setInfoOpp] = useState(null);
  const [toast, setToast] = useState('');
  const [advancing, setAdvancing] = useState(false);
  const [calendarAnchor, setCalendarAnchor] = useState(null);
  const firstMonth = dateToYearMonth(days[0].date);
  const [viewYear, setViewYear] = useState(firstMonth.year);
  const [viewMonth, setViewMonth] = useState(firstMonth.month);
  const animRef = useRef({ cancelled: false, timer: null });
  const calendarOpen = Boolean(calendarAnchor);

  useEffect(() => {
    animRef.current.cancelled = false;
    const month = dateToYearMonth(days[0].date);
    setDayIndex(0);
    setPicks({});
    setAdvancing(false);
    setCalendarAnchor(null);
    setViewYear(month.year);
    setViewMonth(month.month);
    return () => {
      animRef.current.cancelled = true;
      if (animRef.current.timer) window.clearTimeout(animRef.current.timer);
    };
  }, [sessionId, days]);

  const viewDay = days[dayIndex] || days[0];
  const clockDate = viewDay.date;
  const completed = Boolean(viewDay.completed || readonlyQuery);

  const cashRatio = viewDay.equity > 0 ? viewDay.cash / viewDay.equity : null;
  const holdingsValue = Math.max(0, Number(viewDay.equity) - Number(viewDay.cash));
  const hasOpps = (viewDay.opps || []).length > 0;
  const showEquityDelta = typeof viewDay.equityDelta === 'number' && viewDay.equityDelta !== 0;
  const eventMarks = useMemo(
    () => (calendarOpen ? collectEventMarks(days, clockDate) : {}),
    [calendarOpen, days, clockDate],
  );
  const elapsedDays = useMemo(
    () => countTradingDaysInclusive(BACKTEST_START, clockDate),
    [clockDate],
  );
  const totalDays = useMemo(
    () => countTradingDaysInclusive(BACKTEST_START, BACKTEST_END),
    [],
  );
  const sessionPct = totalDays > 0 ? Math.min(100, (elapsedDays / totalDays) * 100) : 0;
  const canPrevMonth = canShiftMonth(viewYear, viewMonth, -1, BACKTEST_START, BACKTEST_END);
  const canNextMonth = canShiftMonth(viewYear, viewMonth, 1, BACKTEST_START, BACKTEST_END);

  const bill = useMemo(() => {
    const items = [];
    (viewDay.opps || []).forEach((row) => {
      const shares = Number(picks[row.id] || 0);
      if (shares > 0) items.push({ ...row, shares, notional: shares * row.price });
    });
    return items;
  }, [viewDay.opps, picks]);

  const billTotal = bill.reduce((sum, row) => sum + row.notional, 0);

  const infoChart = useMemo(() => {
    if (!infoOpp) return {};
    return buildStockKlineChartOptionFromPayload({
      candles: buildMockCandles(viewDay.date, infoOpp.price),
      markers: [{ type: 'opportunity', date: viewDay.date.replace(/-/g, ''), label: '当前日' }],
    });
  }, [viewDay.date, infoOpp]);

  const holdingColumns = [
    { field: 'ticker', headerName: '标的', minWidth: 110, flex: 1 },
    { field: 'name', headerName: '名称', minWidth: 90, flex: 0.8 },
    {
      field: 'shares',
      headerName: '股数',
      width: 88,
      valueFormatter: (p) => Number(p.value).toLocaleString(),
    },
    { field: 'buy', headerName: '买入', minWidth: 140, flex: 1.1 },
    { field: 'pnl', headerName: '浮动', width: 110 },
  ];

  const oppColumns = [
    { field: 'id', headerName: '#', width: 56 },
    { field: 'ticker', headerName: '代码', minWidth: 110, flex: 0.7 },
    { field: 'name', headerName: '名称', minWidth: 96, flex: 0.7 },
    {
      field: 'price',
      headerName: '买入价',
      width: 100,
      valueFormatter: (p) => formatMoney(p.value),
    },
    { field: 'wr', headerName: '历史胜率', width: 100 },
    { field: 'roi', headerName: '平均 ROI', width: 100 },
    {
      field: 'shares',
      headerName: '股数',
      width: 120,
      sortable: false,
      renderCell: (grid) => (
        <TextField
          className="decision-shares-input"
          size="small"
          type="number"
          disabled={completed || advancing}
          value={picks[grid.row.id] ?? ''}
          inputProps={{ min: 0, step: 1, 'aria-label': `股数 ${grid.row.ticker}` }}
          onClick={(event) => event.stopPropagation()}
          onMouseDown={(event) => event.stopPropagation()}
          onChange={(event) => {
            const raw = event.target.value;
            setPicks((prev) => {
              const next = { ...prev };
              if (!raw) delete next[grid.row.id];
              else next[grid.row.id] = Number(raw);
              return next;
            });
          }}
        />
      ),
    },
  ];

  const sleep = (ms) => new Promise((resolve) => {
    animRef.current.timer = window.setTimeout(resolve, ms);
  });

  const landOnDate = (date) => {
    const idx = days.findIndex((row) => row.date === date);
    if (idx >= 0) setDayIndex(idx);
    const month = dateToYearMonth(date);
    setViewYear(month.year);
    setViewMonth(month.month);
    setPicks({});
  };

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
    setConfirmOpen(false);
    closeCalendar();
    if (dayIndex >= days.length - 1) {
      setToast('原型只演示到下一抉择日。真实引擎会继续 next。');
      return;
    }
    const target = days[dayIndex + 1];
    const finish = () => {
      landOnDate(target.date);
      setAdvancing(false);
      setToast('已提交当天，停在下一事件日');
    };
    if (prefersReducedMotion()) {
      finish();
      return;
    }
    await sleep(160);
    if (animRef.current.cancelled) return;
    setAdvancing(true);
    await sleep(280);
    if (animRef.current.cancelled) return;
    finish();
  };

  return (
    <PageLayout
      className="decision-page"
      breadcrumbsItems={[{ label: '决策者', to: '/decision' }]}
      breadcrumbsCurrent={`第 ${sessionId} 局`}
      bannerTitle={isNew ? '新决策 · 第 4 局' : `决策者对局 · 第 ${sessionId} 局`}
      bannerDescription="时钟只显示当前停顿日。推进后总进度前移；月历是只读地图，只标注已经发生的事件。"
      bannerRightSlot={(
        <Button component={RouterLink} to="/decision" variant="outlined" size="small">
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
                <Typography className="decision-clock__date">{clockDate}</Typography>
                <Typography className="decision-clock__weekday">{weekdayLabel(clockDate)}</Typography>
              </Box>
              <Button
                size="small"
                variant="outlined"
                className="decision-calendar-toggle"
                aria-haspopup="dialog"
                aria-expanded={calendarOpen}
                onClick={openCalendar}
              >
                查看日历
              </Button>
            </Box>

            <Button
              className="decision-advance-btn"
              variant="contained"
              disabled={completed || advancing}
              startIcon={<NtqIcon name="play" size={16} />}
              onClick={() => setConfirmOpen(true)}
            >
              {advancing ? '推进中' : '推进'}
            </Button>

            <Box className="decision-hud-metrics">
              <Box className="decision-hud-metric">
                <Typography variant="caption" color="text.secondary">账户价值</Typography>
                <Typography variant="h6" className="decision-hud-metric__value">
                  {formatMoney(viewDay.equity)}
                  {showEquityDelta ? (
                    <Box
                      component="span"
                      className={`decision-hud-delta ${viewDay.equityDelta >= 0 ? 'is-up' : 'is-down'}`}
                    >
                      （{formatSignedMoney(viewDay.equityDelta)}）
                    </Box>
                  ) : null}
                </Typography>
              </Box>
              <Box className="decision-hud-metric">
                <Typography variant="caption" color="text.secondary">可用资金</Typography>
                <Typography variant="h6" className="decision-hud-metric__value">
                  {formatMoney(viewDay.cash)}
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
              已走 {elapsedDays} / {totalDays} 个交易日
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
            <CardContent>
              <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="subtitle1" fontWeight={700}>策略与模拟</Typography>
                <Typography variant="caption" color="text.secondary">只读</Typography>
              </Stack>
              {[
                ['策略', DECISION_STRATEGY.key],
                ['版本', String(DECISION_STRATEGY.versionId)],
                ['对局', String(sessionId)],
                ['回测区间', DECISION_STRATEGY.range],
                ['最大同时持有数', String(DECISION_STRATEGY.maxPortfolioSize)],
              ].map(([label, value]) => (
                <Box key={label} className="decision-meta-row">
                  <Typography variant="body2" color="text.secondary">{label}</Typography>
                  <Typography variant="body2">{value}</Typography>
                </Box>
              ))}
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="subtitle1" fontWeight={700}>仓位状态</Typography>
                <Typography variant="caption" color="text.secondary">硬约束</Typography>
              </Stack>
              <Box className="decision-capital-grid">
                <div>
                  <Typography variant="caption" color="text.secondary">持仓 / 上限</Typography>
                  <Typography variant="h6">
                    {(viewDay.holdings || []).length} / {DECISION_STRATEGY.maxPortfolioSize}
                  </Typography>
                </div>
                <div>
                  <Typography variant="caption" color="text.secondary">持仓市值</Typography>
                  <Typography variant="h6">{formatMoney(holdingsValue)}</Typography>
                </div>
                <div>
                  <Typography variant="caption" color="text.secondary">至今最大回撤</Typography>
                  <Typography variant="h6">{formatDrawdown(viewDay.maxDrawdown)}</Typography>
                </div>
                <div>
                  <Typography variant="caption" color="text.secondary">策略 as-of 胜率</Typography>
                  <Typography variant="h6">{DECISION_STRATEGY.strategyWinRate}</Typography>
                </div>
                <div>
                  <Typography variant="caption" color="text.secondary">策略平均 ROI</Typography>
                  <Typography variant="h6">{DECISION_STRATEGY.strategyAvgRoi}</Typography>
                </div>
              </Box>
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="subtitle1" fontWeight={700}>持仓</Typography>
                <Typography variant="caption" color="text.secondary">入场后不可干预</Typography>
              </Stack>
              {(viewDay.holdings || []).length ? (
                <DataGrid
                  autoHeight
                  rows={viewDay.holdings}
                  columns={holdingColumns}
                  localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
                  hideFooter
                  disableRowSelectionOnClick
                  sx={{ border: 0 }}
                />
              ) : (
                <Typography variant="body2" color="text.secondary">当前无持仓</Typography>
              )}
            </CardContent>
          </Card>
        </Box>

        <Box className="decision-right">
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="subtitle1" fontWeight={700}>今日事件</Typography>
                <Typography variant="caption" color="text.secondary">先结算出场，只读</Typography>
              </Stack>
              {(viewDay.events || []).length ? (
                <Stack spacing={1}>
                  {viewDay.events.map((row) => (
                    <Box
                      key={`${row.date}-${row.text}`}
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
                    唯一可改：编号与股数 · 胜率为该标的 as-of
                  </Typography>
                ) : null}
              </Stack>
              {hasOpps ? (
                <DataGrid
                  autoHeight
                  rows={viewDay.opps || []}
                  columns={oppColumns}
                  localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
                  hideFooter
                  disableRowSelectionOnClick
                  onRowClick={(gridParams, event) => {
                    if (event.target.closest('input')) return;
                    setInfoOpp(gridParams.row);
                  }}
                  sx={{
                    border: 0,
                    '& .MuiDataGrid-row': { cursor: 'pointer' },
                  }}
                />
              ) : null}
              {viewDay.note ? (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  {viewDay.note}
                </Typography>
              ) : null}
            </CardContent>
          </Card>
        </Box>
      </Box>

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
                <Typography variant="body2">
                  [{row.id}] {row.name} {row.shares.toLocaleString()} 股
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
          <Button
            onClick={() => {
              setPicks({});
              setConfirmOpen(false);
              setToast('已清空草稿，仍停在当天');
            }}
          >
            重新下单
          </Button>
          <Button variant="contained" onClick={runAdvance}>确认推进</Button>
        </DialogActions>
      </Dialog>

      <Drawer
        anchor="right"
        open={Boolean(infoOpp)}
        onClose={() => setInfoOpp(null)}
        PaperProps={{ sx: { width: { xs: '100%', sm: 560 } } }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            {infoOpp ? `${infoOpp.ticker} ${infoOpp.name}` : 'info'}
          </Typography>
          <IconButton aria-label="关闭" onClick={() => setInfoOpp(null)}>
            <NtqIcon name="cancel" size={18} />
          </IconButton>
        </Box>
        {infoOpp ? (
          <Box sx={{ px: 2, pb: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              as-of {viewDay.date} · K 线停在当前日，不含未来
            </Typography>
            <Stack spacing={0.75} sx={{ mb: 2 }}>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">策略 as-of</Typography>
                <Typography variant="body2">
                  胜率 {DECISION_STRATEGY.strategyWinRate}  平均ROI {DECISION_STRATEGY.strategyAvgRoi}  n={DECISION_STRATEGY.strategySample}
                </Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">本标的 as-of</Typography>
                <Typography variant="body2">
                  胜率 {infoOpp.wr}  平均ROI {infoOpp.roi}
                </Typography>
              </Stack>
            </Stack>
            <ChartPanel
              title="K 线"
              option={infoChart}
              height={280}
              note="不预载全市场；点某一行机会才拉该标的。"
            />
          </Box>
        ) : null}
      </Drawer>

      <Snackbar
        open={Boolean(toast)}
        autoHideDuration={2200}
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
