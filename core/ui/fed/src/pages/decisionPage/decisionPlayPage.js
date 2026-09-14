import React, { useMemo, useState } from 'react';
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
  Drawer,
  IconButton,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import PageLayout from '../../components/pageLayout/pageLayout';
import ChartPanel from '../../components/chartPanel/chartPanel';
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import { buildStockKlineChartOptionFromPayload } from '../strategyWorkbenchPage/panels/strategyReportPanel/lib/stockKlineChart';
import {
  DECISION_STRATEGY,
  SESSION_DAYS,
  buildMockCandles,
  formatMoney,
} from './mockDecisionData';
import './decisionPage.scss';

const CALENDAR_LABEL = {
  past: '已过',
  now: '当前',
  locked: '未到',
};

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

  const day = days[dayIndex] || days[0];
  const completed = Boolean(day.completed || readonlyQuery);

  const bill = useMemo(() => {
    const items = [];
    (day.opps || []).forEach((row) => {
      const shares = Number(picks[row.id] || 0);
      if (shares > 0) items.push({ ...row, shares, notional: shares * row.price });
    });
    return items;
  }, [day.opps, picks]);

  const billTotal = bill.reduce((sum, row) => sum + row.notional, 0);

  const infoChart = useMemo(() => {
    if (!infoOpp) return {};
    return buildStockKlineChartOptionFromPayload({
      candles: buildMockCandles(day.date, infoOpp.price),
      markers: [{ type: 'opportunity', date: day.date.replace(/-/g, ''), label: '当前日' }],
    });
  }, [day.date, infoOpp]);

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
      renderCell: (params) => (
        <TextField
          className="decision-shares-input"
          size="small"
          type="number"
          disabled={completed}
          value={picks[params.row.id] ?? ''}
          inputProps={{ min: 0, step: 100, 'aria-label': `股数 ${params.row.ticker}` }}
          onClick={(event) => event.stopPropagation()}
          onMouseDown={(event) => event.stopPropagation()}
          onChange={(event) => {
            const raw = event.target.value;
            setPicks((prev) => {
              const next = { ...prev };
              if (!raw) delete next[params.row.id];
              else next[params.row.id] = Number(raw);
              return next;
            });
          }}
        />
      ),
    },
  ];

  const confirmAdvance = () => {
    setConfirmOpen(false);
    if (dayIndex >= days.length - 1) {
      setToast('原型只演示到下一抉择日。真实引擎会继续 next。');
      return;
    }
    setDayIndex((n) => n + 1);
    setPicks({});
    setToast('已提交当天，跳到下一抉择日');
  };

  return (
    <PageLayout
      className="decision-page"
      breadcrumbsItems={[{ label: '决策者', to: '/decision' }]}
      breadcrumbsCurrent={`第 ${sessionId} 局`}
      bannerTitle={isNew ? '新决策 · 第 4 局' : `决策者对局 · 第 ${sessionId} 局`}
      bannerDescription="日历只显示有抉择的日子，不可点选跳转。推进先出账单，确认后才提交。"
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
          <Box className="decision-calendar" title="日历为 HUD，不可跳转到某一天">
            {(day.calendar || []).map((cell) => (
              <Chip
                key={`${cell.date}-${cell.state}`}
                size="small"
                color={cell.state === 'now' ? 'primary' : 'default'}
                variant={cell.state === 'now' ? 'filled' : 'outlined'}
                label={`${CALENDAR_LABEL[cell.state]} ${cell.date}`}
              />
            ))}
          </Box>
          <Box className="decision-hud-actions">
            <Box className="decision-hud-metric">
              <Typography variant="caption" color="text.secondary">现金</Typography>
              <Typography variant="h6">{formatMoney(day.cash)}</Typography>
            </Box>
            <Box className="decision-hud-metric">
              <Typography variant="caption" color="text.secondary">当前日</Typography>
              <Typography variant="h6">{day.date}</Typography>
            </Box>
            <Button
              variant="contained"
              disabled={completed}
              onClick={() => setConfirmOpen(true)}
            >
              推进
            </Button>
          </Box>
        </CardContent>
      </Card>

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
                ['version', String(DECISION_STRATEGY.versionId)],
                ['session', String(sessionId)],
                ['区间', DECISION_STRATEGY.range],
                ['max_portfolio_size', String(DECISION_STRATEGY.maxPortfolioSize)],
                ['手数', `${DECISION_STRATEGY.lotSize} 股`],
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
                <Typography variant="subtitle1" fontWeight={700}>资金仓位</Typography>
                <Typography variant="caption" color="text.secondary">硬约束</Typography>
              </Stack>
              <Box className="decision-capital-grid">
                <div>
                  <Typography variant="caption" color="text.secondary">现金</Typography>
                  <Typography variant="h6">{formatMoney(day.cash)}</Typography>
                </div>
                <div>
                  <Typography variant="caption" color="text.secondary">持仓 / 上限</Typography>
                  <Typography variant="h6">
                    {(day.holdings || []).length} / {DECISION_STRATEGY.maxPortfolioSize}
                  </Typography>
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
              {(day.holdings || []).length ? (
                <DataGrid
                  autoHeight
                  rows={day.holdings}
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
                <Typography variant="subtitle1" fontWeight={700}>当天 event</Typography>
                <Typography variant="caption" color="text.secondary">先结算出场，只读</Typography>
              </Stack>
              {(day.events || []).length ? (
                <Stack spacing={1}>
                  {day.events.map((row) => (
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
                  本日无出场通报（空日已跳过，不占日历格）。
                </Typography>
              )}
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="subtitle1" fontWeight={700}>新机会</Typography>
                <Typography variant="caption" color="text.secondary">
                  唯一可改：编号与股数 · 胜率为该标的 as-of
                </Typography>
              </Stack>
              <DataGrid
                autoHeight
                rows={day.opps || []}
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
              {day.note ? (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  {day.note}
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
            提交后不可改当日选择。空选择等于本日不买，时钟跳到下一抉择日。
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
          <Button variant="contained" onClick={confirmAdvance}>确认推进</Button>
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
              as-of {day.date} · K 线停在当前日，不含未来
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
