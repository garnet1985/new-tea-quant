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
  fetchStrategyScanReadiness,
  getStrategyWorkbenchPath,
  startStrategyScan,
} from '../../api/apis/strategyApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import './scanPage.scss';

const PROTOTYPE_DATA_ASOF_DATE = '2025-12-30';
// 报告生成时间（可选显示）
const SHOW_REPORT_GENERATED_AT = false;

function formatScanDate(v) {
  const raw = String(v || '').trim();
  if (!raw) return '';
  // yyyy-mm-dd
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  // yyyymmdd
  if (/^\d{8}$/.test(raw)) return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
  return raw;
}

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
  const [reportVisible, setReportVisible] = useState(false);
  const [reportStrategyId, setReportStrategyId] = useState('');
  const [reportStrategyName, setReportStrategyName] = useState('');
  const [scanTriggeredAt, setScanTriggeredAt] = useState('');
  const [reportGeneratedAt, setReportGeneratedAt] = useState('');
  const [reportDemo, setReportDemo] = useState(null); // null | boolean

  /** run | rerun — 与 GET …/scan 的 `primary_action` 对齐，仅影响按钮文案 */
  const [scanPrimaryById, setScanPrimaryById] = useState({});

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailStrategyId, setDetailStrategyId] = useState('');

  const pollRef = useRef({ timeoutId: null });
  const running = Boolean(runningStrategyId) && Boolean(runningJobId);

  const reportPayload = useMemo(() => results?.[reportStrategyId] || null, [results, reportStrategyId]);
  const detailPayload = useMemo(() => results?.[detailStrategyId] || null, [results, detailStrategyId]);
  const detailStrategyName = useMemo(() => {
    if (!detailStrategyId) return '';
    return rows.find((r) => r.id === detailStrategyId)?.name || detailStrategyId;
  }, [detailStrategyId, rows]);

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

  const refreshScanPrimaryActions = useCallback(() => {
    const demo = mode === 'demo';
    const list = Array.isArray(rows) ? rows.filter((r) => r?.name) : [];
    if (list.length === 0) {
      setScanPrimaryById({});
      return;
    }
    Promise.all(
      list.map((r) => fetchStrategyScanReadiness(r.name, { demo }).then((x) => ({
        id: r.id,
        action: x.primary_action === 'rerun' ? 'rerun' : 'run',
        report: x.report,
      }))),
    )
      .then((pairs) => {
        const next = {};
        pairs.forEach(({ id, action }) => {
          next[id] = action;
        });
        setScanPrimaryById(next);
        setResults((prev) => {
          const o = { ...(prev || {}) };
          pairs.forEach(({ id, action, report }) => {
            if (report && typeof report === 'object') {
              o[id] = report;
            } else if (action === 'run') {
              delete o[id];
            }
          });
          return o;
        });
      })
      .catch(() => {
        setScanPrimaryById({});
      });
  }, [rows, mode]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    refreshScanPrimaryActions();
  }, [refreshScanPrimaryActions]);

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
        <Chip size="small" color="success" label="已启用" />
      ) : (
        <Chip size="small" color="default" label="已禁用" />
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
        const isRerun = scanPrimaryById[id] === 'rerun';
        const disableRun = !enabled || running;
        return (
          <Stack direction="row" spacing={1} alignItems="center">
            <Button
              size="small"
              variant="contained"
              disabled={disableRun}
              title={
                isRerun
                  ? '将全量重新扫描并忽略已保存的扫描结果'
                  : '尚无已保存结果时全量扫描；按住 Shift 再点击可强制重新扫描'
              }
              onClick={(e) => {
                e.stopPropagation();
                if (!enabled || running) return;
                const force = isRerun || e.shiftKey;
                setRunError('');
                setReportVisible(false);
                setReportStrategyId('');
                setScanTriggeredAt(new Date().toLocaleString('zh-CN', { hour12: false }));
                setProgress({ pct: 0, label: '准备扫描…' });
                startStrategyScan(params.row.name, { demo: mode === 'demo', force })
                  .then((res) => {
                    const jobId = String(res?.job_id || '').trim();
                    if (!jobId) throw new Error('启动失败：未返回 job_id');
                    setRunningStrategyId(id);
                    setRunningJobId(jobId);
                    setReportDemo(Boolean(res?.demo));
                  })
                  .catch((err) => {
                    setRunError(err?.message || '启动扫描失败');
                  });
              }}
            >
              {isRerun ? '重新扫描' : '开始扫描'}
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
  ]), [mode, progress.pct, results, running, runningStrategyId, scanPrimaryById]);

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
            setReportStrategyId(runningStrategyId);
            setReportStrategyName(strategyName);
            setReportGeneratedAt(new Date().toLocaleString('zh-CN', { hour12: false }));
            if (typeof p?.demo === 'boolean') setReportDemo(p.demo);
            setReportVisible(true);
            setRunningStrategyId('');
            setRunningJobId('');
            window.setTimeout(() => {
              refreshScanPrimaryActions();
            }, 0);
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
  }, [mode, rows, running, runningJobId, runningStrategyId, refreshScanPrimaryActions]);

  return (
    <PageLayout
      className="scan-page"
      breadcrumbsItems={[{ label: '策略实验室', to: '/strategy-workbench' }]}
      breadcrumbsCurrent="策略选股"
      bannerTitle="策略选股"
      bannerDescription={(
        <>
          勾选下方<strong>已启用</strong>的策略，在全市场范围内按规则筛选机会；每个策略按其配置的标的域（target）分别执行。
        </>
      )}
      bannerRightSlot={(
        <Chip
          label={running ? '扫描中…' : '就绪'}
          color={running ? 'warning' : 'default'}
          variant={running ? 'filled' : 'outlined'}
        />
      )}
    >

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
              <Stack direction="row" spacing={1.25} alignItems="center" flexWrap="wrap" justifyContent="flex-end">
                <Typography variant="caption" color="text.secondary">
                  扫描当日：{scanTriggeredAt || reportGeneratedAt || '—'}
                </Typography>
                {SHOW_REPORT_GENERATED_AT ? (
                  <Typography variant="caption" color="text.secondary">
                    报告日期：{reportGeneratedAt || '—'}
                  </Typography>
                ) : null}
              </Stack>
            </Stack>
            <Typography variant="body2" sx={{ mb: 0.75 }}>
              使用策略
              {' '}
              <strong>{reportStrategyName || reportStrategyId || '—'}</strong>
              {' '}
              扫描完成：共找到
              {' '}
              <Button
                size="small"
                variant="text"
                sx={{ minWidth: 'unset', px: 0.5, fontWeight: 700, lineHeight: 1.2 }}
                onClick={(e) => {
                  e.stopPropagation();
                  if (!reportStrategyId) return;
                  openDetail(reportStrategyId);
                }}
              >
                {Number(reportPayload?.total_opportunities ?? 0)}
              </Button>
              {' '}
              个机会
            </Typography>
            <Box sx={{ pl: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.25 }}>
                - 扫描日期：{formatScanDate(reportPayload?.date) || '—'}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.25 }}>
                - 总扫描股票数：{Number(reportPayload?.total_stocks ?? 0) || '—'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                - 模式：{reportDemo === true ? '演示模式' : '严格模式'}
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
              请点击表格里的机会数量查看详情。
            </Typography>
          </CardContent>
        </Card>
      ) : null}

      <Dialog open={detailOpen} onClose={closeDetail} maxWidth="md" fullWidth>
        <DialogTitle>
          机会明细 · {detailStrategyName || '—'}
        </DialogTitle>
        <DialogContent dividers sx={{ height: 520 }}>
          {detailPayload ? (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                机会明细与 CLI 输出对齐；可分页查看。
              </Typography>
              {(() => {
                const rows0 = Array.isArray(detailPayload?.opportunities) ? detailPayload.opportunities : [];
                const dates = Array.from(new Set(
                  rows0
                    .map((o) => formatScanDate(o?.trigger_date || o?.triggerDate))
                    .filter(Boolean),
                ));
                if (!dates.length) return null;
                dates.sort();
                const label = dates.length === 1 ? dates[0] : `${dates[0]} ~ ${dates[dates.length - 1]}（多日）`;
                return (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.25 }}>
                    触发日期：{label}
                  </Typography>
                );
              })()}
              <Box sx={{ width: '100%', height: 420 }}>
                <DataGrid
                  rows={(() => {
                    const ops = Array.isArray(detailPayload?.opportunities) ? detailPayload.opportunities : null;
                    if (ops) {
                      return ops.map((o, idx) => ({
                        id: String(o?.stock_id || o?.stockId || `${idx}`),
                        stock_id: String(o?.stock_id || o?.stockId || ''),
                        stock_name: String(o?.stock_name || o?.stockName || ''),
                        trigger_price: o?.trigger_price ?? o?.triggerPrice ?? '',
                        extra_fields: o?.extra_fields ?? o?.extraFields ?? {},
                      }));
                    }
                    const list = Array.isArray(detailPayload?.summary?.stocks_with_opportunities)
                      ? detailPayload.summary.stocks_with_opportunities
                      : [];
                    return list.map((code) => ({ id: code, stock_id: code, stock_name: '', trigger_price: '', extra_fields: {} }));
                  })()}
                  columns={[
                    { field: 'stock_id', headerName: '股票代码', minWidth: 140, flex: 0.6 },
                    { field: 'stock_name', headerName: '名称', minWidth: 140, flex: 0.6 },
                    {
                      field: 'trigger_price',
                      headerName: '触发价格',
                      minWidth: 120,
                      flex: 0.5,
                      valueFormatter: (v) => (v?.value === '' || v?.value == null ? '—' : String(v.value)),
                    },
                    {
                      field: 'extra_fields',
                      headerName: '额外信息',
                      minWidth: 220,
                      flex: 1,
                      valueGetter: (params) => {
                        const v = params?.row?.extra_fields;
                        if (!v || (typeof v === 'object' && Object.keys(v).length === 0)) return '';
                        return typeof v === 'string' ? v : JSON.stringify(v);
                      },
                      renderCell: (params) => (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                        >
                          {params.value || '—'}
                        </Typography>
                      ),
                    },
                  ]}
                  localeText={zhCN}
                  disableRowSelectionOnClick
                  pagination
                  pageSizeOptions={[10, 25, 50]}
                  initialState={{
                    pagination: { paginationModel: { page: 0, pageSize: 10 } },
                  }}
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
    </PageLayout>
  );
}

export default ScanPage;

