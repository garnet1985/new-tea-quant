import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
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
  FormControl,
  FormControlLabel,
  LinearProgress,
  Link,
  Radio,
  RadioGroup,
  Stack,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  fetchStrategyList,
  fetchStrategyScanProgress,
  getStrategyWorkbenchPath,
  startStrategyScan,
} from '../../api/apis/strategyApi';
import './scanPage.scss';

const PROTOTYPE_DATA_ASOF_DATE = '2025-12-30';

function ScanPage() {
  const [mode, setMode] = useState('demo');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const [runningStrategyId, setRunningStrategyId] = useState('');
  const [runningJobId, setRunningJobId] = useState('');
  const [runError, setRunError] = useState('');
  const [progress, setProgress] = useState({ pct: 0, label: '准备扫描…' });

  const [results, setResults] = useState({}); // strategy_id -> report payload
  const [reportMeta, setReportMeta] = useState('');
  const [reportVisible, setReportVisible] = useState(false);
  const [reportStrategyId, setReportStrategyId] = useState('');

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailStrategyId, setDetailStrategyId] = useState('');

  const pollRef = useRef({ timeoutId: null });
  const running = Boolean(runningStrategyId) && Boolean(runningJobId);

  const reportPayload = useMemo(() => results?.[reportStrategyId] || null, [results, reportStrategyId]);
  const detailPayload = useMemo(() => results?.[detailStrategyId] || null, [results, detailStrategyId]);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchStrategyList()
      .then((res) => {
        setRows(Array.isArray(res?.data) ? res.data : []);
      })
      .catch((e) => {
        setRows([]);
        setLoadError(e?.message || '加载策略列表失败');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => () => {
    if (pollRef.current.timeoutId) window.clearTimeout(pollRef.current.timeoutId);
  }, []);

  const openDetail = (strategyId) => {
    if (!strategyId) return;
    if (!results?.[strategyId]) return;
    setDetailStrategyId(strategyId);
    setDetailOpen(true);
  };

  const closeDetail = () => {
    setDetailOpen(false);
    setDetailStrategyId('');
  };

  const columns = useMemo(() => ([
    {
      field: 'name',
      headerName: '策略',
      minWidth: 200,
      flex: 0.6,
      renderCell: (params) => (
        <Stack spacing={0.5}>
          <Typography variant="body2" fontWeight={700}>{params.row.name}</Typography>
          <Typography variant="caption" color="text.secondary">{params.row.description || '—'}</Typography>
        </Stack>
      ),
    },
    {
      field: 'is_enabled',
      headerName: '启用',
      width: 110,
      renderCell: (params) => (params.value ? (
        <Chip size="small" color="success" label="Enabled" />
      ) : (
        <Chip size="small" color="default" label="Disabled" />
      )),
    },
    {
      field: 'opportunities',
      headerName: '机会数量',
      width: 120,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const id = params.row.id;
        const enabled = Boolean(params.row.is_enabled);
        const pack = results?.[id];
        if (!enabled || !pack) return <Typography variant="body2" color="text.secondary">—</Typography>;
        const n = Number(pack?.total_opportunities ?? pack?.totalOpportunities ?? pack?.opportunity_count ?? 0);
        return (
          <Button
            size="small"
            variant="text"
            onClick={(e) => {
              e.stopPropagation();
              openDetail(id);
            }}
          >
            {n}
          </Button>
        );
      },
    },
    {
      field: 'actions',
      headerName: '',
      width: 210,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const enabled = Boolean(params.row.is_enabled);
        const id = params.row.id;
        const isThisRunning = running && id === runningStrategyId;
        const disableRun = !enabled || running;
        return (
          <Stack direction="row" spacing={1} alignItems="center">
            <Button
              size="small"
              variant="contained"
              disabled={disableRun}
              onClick={(e) => {
                e.stopPropagation();
                if (!enabled || running) return;
                setRunError('');
                setReportVisible(false);
                setReportStrategyId('');
                setProgress({ pct: 0, label: '准备扫描…' });
                startStrategyScan(params.row.name, { demo: mode === 'demo' })
                  .then((res) => {
                    const jobId = String(res?.job_id || '').trim();
                    if (!jobId) throw new Error('启动失败：未返回 job_id');
                    setRunningStrategyId(id);
                    setRunningJobId(jobId);
                  })
                  .catch((err) => {
                    setRunError(err?.message || '启动扫描失败');
                  });
              }}
            >
              开始扫描
            </Button>
            <Link
              component={RouterLink}
              to={getStrategyWorkbenchPath(params.row.name)}
              underline="hover"
              onClick={(e) => e.stopPropagation()}
              sx={{ fontSize: 13 }}
            >
              调试策略
            </Link>
            {isThisRunning ? (
              <Typography variant="caption" color="text.secondary">
                {Math.round(progress.pct)}%
              </Typography>
            ) : null}
          </Stack>
        );
      },
    },
  ]), [mode, progress.pct, results, running, runningStrategyId]);

  useEffect(() => {
    if (!running) return undefined;
    const strategyName = rows.find((r) => r.id === runningStrategyId)?.name || '';
    if (!strategyName) return undefined;

    let cancelled = false;

    const pollOnce = () => {
      fetchStrategyScanProgress(strategyName, runningJobId)
        .then((p) => {
          if (cancelled) return;
          const pct = Number(p?.progress ?? 0);
          const status = String(p?.status || '');
          const total = p?.total_jobs != null ? Number(p.total_jobs) : null;
          const done = p?.done_jobs != null ? Number(p.done_jobs) : null;
          const label = total != null && done != null
            ? `扫描中…（${done}/${total}）`
            : status === 'completed' ? '写入报告…' : '扫描中…';
          setProgress({ pct: Number.isFinite(pct) ? pct : 0, label });

          if (status === 'completed') {
            const report = p?.report && typeof p.report === 'object' ? p.report : {};
            setResults((prev) => ({ ...(prev || {}), [runningStrategyId]: report }));
            const modeLabel = mode === 'strict'
              ? '严格模式（服务端校验数据已对齐最新交易日）'
              : `扫描演示（截止 ${PROTOTYPE_DATA_ASOF_DATE}）`;
            setReportMeta(`${modeLabel} · ${new Date().toLocaleString('zh-CN', { hour12: false })}`);
            setReportStrategyId(runningStrategyId);
            setReportVisible(true);
            setRunningStrategyId('');
            setRunningJobId('');
            return;
          }
          if (status === 'failed') {
            setRunError(String(p?.reason || '扫描失败'));
            setRunningStrategyId('');
            setRunningJobId('');
            return;
          }

          pollRef.current.timeoutId = window.setTimeout(pollOnce, 600);
        })
        .catch((err) => {
          if (cancelled) return;
          setRunError(err?.message || '轮询扫描进度失败');
          setRunningStrategyId('');
          setRunningJobId('');
        });
    };

    pollOnce();
    return () => {
      cancelled = true;
      if (pollRef.current.timeoutId) window.clearTimeout(pollRef.current.timeoutId);
    };
  }, [mode, rows, running, runningJobId, runningStrategyId]);

  return (
    <Box className="scan-page" sx={{ p: 2, width: '100%' }}>
      <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
        <Box>
          <Typography component="h1" variant="h5" sx={{ fontWeight: 700, mb: 0.75 }}>
            机会扫描
          </Typography>
          <Typography variant="body2" color="text.secondary">
            勾选下方<strong>已启用</strong>的策略，对当前市场机会进行批量扫描；每个策略按其配置的标的域（target）分别执行。
          </Typography>
        </Box>
        <Chip
          label={running ? '扫描中…' : '就绪'}
          color={running ? 'warning' : 'default'}
          variant={running ? 'filled' : 'outlined'}
        />
      </Stack>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1.5} sx={{ mb: 1 }}>
            <Typography variant="subtitle1" fontWeight={700}>扫描模式</Typography>
            <Typography variant="caption" color="text.secondary">接入数据服务后由服务端校验</Typography>
          </Stack>
          <FormControl component="fieldset">
            <RadioGroup
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              aria-label="扫描模式"
              className="scan-mode-options"
            >
              <FormControlLabel
                value="strict"
                control={<Radio disabled={running} />}
                label={(
                  <Box className="scan-mode-option-body">
                    <Typography variant="body2" fontWeight={700}>严格模式</Typography>
                    <Typography variant="body2" color="text.secondary">
                      仅当行情、因子等依赖数据均已更新至<strong>最新交易日</strong>后才允许执行扫描；不满足则中断并提示缺口。
                    </Typography>
                  </Box>
                )}
                className={[
                  'scan-mode-option',
                  mode === 'strict' ? 'scan-mode-option--active' : '',
                  running ? 'scan-mode-option--disabled' : '',
                ].filter(Boolean).join(' ')}
                sx={{ alignItems: 'flex-start' }}
              />
              <FormControlLabel
                value="demo"
                control={<Radio disabled={running} />}
                label={(
                  <Box className="scan-mode-option-body">
                    <Typography variant="body2" fontWeight={700}>扫描演示</Typography>
                    <Typography variant="body2" color="text.secondary">
                      以数据集中<strong>已有最新日期</strong>作为扫描截止日（占位：
                      {' '}
                      <strong>{PROTOTYPE_DATA_ASOF_DATE}</strong>
                      ），用于演示链路，不代表实时市场。
                    </Typography>
                  </Box>
                )}
                className={[
                  'scan-mode-option',
                  mode === 'demo' ? 'scan-mode-option--active' : '',
                  running ? 'scan-mode-option--disabled' : '',
                ].filter(Boolean).join(' ')}
                sx={{ alignItems: 'flex-start' }}
              />
            </RadioGroup>
          </FormControl>
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            alignItems={{ xs: 'stretch', md: 'center' }}
            justifyContent="space-between"
            spacing={1.5}
            sx={{ mb: 1 }}
          >
            <Stack direction="row" alignItems="center" spacing={1.25} flexWrap="wrap">
              <Button
                variant="outlined"
                disabled={running}
                onClick={load}
              >
                刷新策略列表
              </Button>
            </Stack>
            <Typography variant="caption" color="text.secondary">
              提示：一次仅允许扫描一个策略；运行中会禁用其它策略的扫描按钮。
            </Typography>
          </Stack>

          {loadError ? <Alert severity="error" sx={{ mb: 1.5 }}>{loadError}</Alert> : null}
          {runError ? <Alert severity="error" sx={{ mb: 1.5 }}>{runError}</Alert> : null}

          {running ? (
            <Box sx={{ mb: 1.5 }}>
              <div className="scan-progress-row">
                <div style={{ flex: 1 }}>
                  <LinearProgress variant="determinate" value={progress.pct} />
                </div>
                <Typography variant="caption" color="text.secondary" className="scan-progress-label">
                  {progress.label}
                </Typography>
              </div>
            </Box>
          ) : null}

          <Box sx={{ width: '100%' }}>
            <DataGrid
              autoHeight
              rows={rows}
              columns={columns}
              loading={loading}
              localeText={zhCN}
              disableRowSelectionOnClick
              pageSizeOptions={[10]}
              initialState={{
                pagination: { paginationModel: { page: 0, pageSize: 10 } },
              }}
            />
          </Box>
        </CardContent>
      </Card>

      {reportVisible ? (
        <Card variant="outlined">
          <CardContent>
            <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1.5} sx={{ mb: 1 }}>
              <Typography variant="subtitle1" fontWeight={700}>扫描报告</Typography>
              <Typography variant="caption" color="text.secondary">{reportMeta}</Typography>
            </Stack>
            <Typography variant="body2" sx={{ mb: 1 }}>
              策略
              {' '}
              <strong>{reportStrategyId || '—'}</strong>
              {' '}
              扫描完成；命中
              {' '}
              <strong>{Number(reportPayload?.total_opportunities ?? 0)}</strong>
              {' '}
              条机会，覆盖
              {' '}
              <strong>{Number(reportPayload?.total_stocks ?? 0)}</strong>
              {' '}
              只股票。
            </Typography>
            <Typography variant="caption" color="text.secondary">
              正式环境：严格模式下若数据未更新至最新交易日将拦截；演示模式以数据集中最新已有交易日为截止。
            </Typography>
          </CardContent>
        </Card>
      ) : null}

      <Dialog open={detailOpen} onClose={closeDetail} maxWidth="sm" fullWidth>
        <DialogTitle>
          机会明细 · {detailStrategyId || '—'}
        </DialogTitle>
        <DialogContent dividers>
          {detailPayload ? (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                当前后端 report 为摘要；机会明细（股票列表/建议买入价）将于下一步在扫描结果落盘后补齐。
              </Typography>
              <Box sx={{ width: '100%' }}>
                <DataGrid
                  autoHeight
                  rows={Array.isArray(detailPayload?.summary?.stocks_with_opportunities)
                    ? detailPayload.summary.stocks_with_opportunities.map((code) => ({ id: code, code }))
                    : []}
                  columns={[
                    { field: 'code', headerName: '代码', minWidth: 180, flex: 1 },
                  ]}
                  localeText={zhCN}
                  disableRowSelectionOnClick
                  hideFooter
                />
              </Box>
            </>
          ) : (
            <Typography variant="body2" color="text.secondary">
              暂无明细。
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDetail}>关闭</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ScanPage;

