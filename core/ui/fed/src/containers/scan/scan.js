import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  LinearProgress,
  Radio,
  RadioGroup,
  Stack,
  Switch,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  fetchStrategyList,
  fetchStrategyScanContext,
  fetchStrategyScanProgress,
  fetchStrategyScanReadiness,
  getStrategyDisplayLabel,
  getStrategyDesignPath,
  startStrategyScan,
} from '../../api/strategyApi';
import {
  fetchPostProcessProcessors,
  setPostProcessRunEnabled,
} from '../../api/postProcessApi';
import {
  groupStrategiesByCategory,
  readStrategyListCategoryQuery,
  STRATEGY_LIST_CATEGORY_PARAM,
} from 'containers/strategyCategory';
import PageLayout from '../../views/pageLayout';
import { SectionBlock } from '../../views/sectionBlock';
import CountBadge from '../../views/countBadge';
import CountTab from '../../views/countTab';
import SearchField from '../../views/searchField';
import DataEndTruncationAlert from '../../views/dataEndTruncationAlert';
import Message from 'views/message';
import StrategyDescriptionText from '../../views/strategyDescriptionText';
import InlineLoadingState from '../../views/inlineLoadingState';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../views/dataGridLoadingOverlay';
import NtqIcon from '../../views/ntqIcon';
import { buildStrategyDesignNavState } from 'containers/strategyDesign';
import { notifyTaskSuccess } from '../../service/feedbackPromptBus';
import { formatDateTime } from '../../service/format/formatDateTime';
import {
  OpportunityDetailMeta,
  buildOpportunityColumns,
  formatSessionSummaryLine,
  mapOpportunityRow,
  readPresenterHistory,
  readPresenterScanUi,
} from './presenterScanReport';
import './style.scss';

function readOpportunityCount(pack) {
  if (!pack || typeof pack !== 'object') return null;
  const raw = pack.total_opportunities ?? pack.totalOpportunities ?? pack.opportunity_count;
  if (raw == null || raw === '') return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

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

function Scan() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [mode, setMode] = useState('demo');
  const [dataEnd, setDataEnd] = useState({});
  const [demoScanCutoffDate, setDemoScanCutoffDate] = useState('');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pageReady, setPageReady] = useState(false);
  const [contextLoading, setContextLoading] = useState(true);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [readinessError, setReadinessError] = useState('');
  const [nameQuery, setNameQuery] = useState('');

  const [runningStrategyId, setRunningStrategyId] = useState('');
  const [runningJobId, setRunningJobId] = useState('');
  const [runError, setRunError] = useState('');
  const [progress, setProgress] = useState({ pct: 0, label: '准备扫描…' });

  const [results, setResults] = useState({}); // strategy_id -> report payload
  const [postProcessors, setPostProcessors] = useState([]);
  /** 本次扫描是否运行已启用的扫描后处理（不改全局 is_enabled） */
  const [runPostProcess, setRunPostProcess] = useState(true);
  const [reportVisible, setReportVisible] = useState(false);
  const [reportStrategyId, setReportStrategyId] = useState('');
  const [reportStrategyName, setReportStrategyName] = useState('');
  const [scanTriggeredAt, setScanTriggeredAt] = useState('');
  const [reportGeneratedAt, setReportGeneratedAt] = useState('');
  const [reportDemo, setReportDemo] = useState(null); // null | boolean

  /** run | rerun — 与 GET …/scan 的 `primary_action` 对齐，仅影响按钮文案 */
  const [scanPrimaryById, setScanPrimaryById] = useState({});
  /** 严格模式数据门禁：策略 id → 是否可扫 / 阻断原因 */
  const [scanGateById, setScanGateById] = useState({});
  const [strictBlockReason, setStrictBlockReason] = useState('');

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailStrategyId, setDetailStrategyId] = useState('');

  const pollRef = useRef({ timeoutId: null });
  const readinessReqRef = useRef(0);
  const selectedChipRef = useRef(null);
  const running = Boolean(runningStrategyId) && Boolean(runningJobId);

  const categoryQuery = readStrategyListCategoryQuery(searchParams);

  const reportPayload = useMemo(() => results?.[reportStrategyId] || null, [results, reportStrategyId]);
  const detailPayload = useMemo(() => results?.[detailStrategyId] || null, [results, detailStrategyId]);
  // SPECIAL-CASE DEC-05：presenter 只给机会表追加回测列；见 post_process/docs/DECISIONS.md
  // 「执行扫描后处理」关闭时不读落盘里的旧 presenter 载荷
  const detailPresenterUi = useMemo(() => {
    if (!runPostProcess || detailPayload?.post_process?.skipped) return null;
    return readPresenterScanUi(detailPayload);
  }, [detailPayload, runPostProcess]);
  const detailStrategyName = useMemo(() => {
    if (!detailStrategyId) return '';
    const row = rows.find((r) => r.id === detailStrategyId);
    return getStrategyDisplayLabel(row) || detailStrategyId;
  }, [detailStrategyId, rows]);
  const detailPresenterHistory = useMemo(() => {
    const key = String(
      detailPayload?.strategy_key
      || detailPayload?.strategyKey
      || detailStrategyId
      || '',
    ).trim();
    return readPresenterHistory(detailPresenterUi, key);
  }, [detailPresenterUi, detailPayload, detailStrategyId]);

  const catalogGroups = useMemo(() => groupStrategiesByCategory(rows), [rows]);

  const categoryFilteredRows = useMemo(() => {
    if (!categoryQuery) return rows;
    const match = catalogGroups.find((g) => g.queryValue === categoryQuery);
    return match ? match.rows : [];
  }, [rows, categoryQuery, catalogGroups]);

  const catalogHasSelectedCategory = Boolean(
    !categoryQuery || catalogGroups.some((g) => g.queryValue === categoryQuery),
  );

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return categoryFilteredRows;
    return categoryFilteredRows.filter((r) => {
      const id = String(r.name || '').toLowerCase();
      const path = String(r.path || '').toLowerCase();
      const key = String(r.key || '').toLowerCase();
      const label = String(r.display_name || getStrategyDisplayLabel(r) || '').toLowerCase();
      const desc = String(r.description || '').toLowerCase();
      const category = String(r.category || '').toLowerCase();
      return (
        id.includes(q)
        || path.includes(q)
        || key.includes(q)
        || label.includes(q)
        || desc.includes(q)
        || category.includes(q)
      );
    });
  }, [categoryFilteredRows, nameQuery]);

  const groupedRows = useMemo(
    () => groupStrategiesByCategory(displayRows),
    [displayRows],
  );

  const setCategoryQuery = useCallback((nextQuery) => {
    const q = String(nextQuery || '').trim();
    if (q === categoryQuery) return;
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (q) next.set(STRATEGY_LIST_CATEGORY_PARAM, q);
      else next.delete(STRATEGY_LIST_CATEGORY_PARAM);
      return next;
    });
  }, [categoryQuery, setSearchParams]);

  const toggleCategoryQuery = useCallback((queryValue) => {
    const q = String(queryValue || '').trim();
    setCategoryQuery(q && q === categoryQuery ? '' : q);
  }, [categoryQuery, setCategoryQuery]);

  const load = useCallback(() => {
    setLoading(true);
    setContextLoading(true);
    setReadinessLoading(true);
    readinessReqRef.current += 1;
    setLoadError('');
    setScanPrimaryById({});
    setScanGateById({});

    fetchStrategyList()
      .then((listRes) => {
        setRows(Array.isArray(listRes?.data) ? listRes.data : []);
      })
      .catch((e) => {
        setRows([]);
        setLoadError(e?.message || '加载策略列表失败');
      })
      .finally(() => {
        setLoading(false);
        setPageReady(true);
      });

    fetchStrategyScanContext()
      .then((ctxRes) => {
        setDataEnd(ctxRes?.dataEnd && typeof ctxRes.dataEnd === 'object' ? ctxRes.dataEnd : {});
        setDemoScanCutoffDate(String(ctxRes?.demoScanCutoffDate || '').trim());
        setRunPostProcess(ctxRes?.enablePostProcess !== false);
      })
      .catch(() => {
        setDataEnd({});
        setDemoScanCutoffDate('');
      })
      .finally(() => setContextLoading(false));

    fetchPostProcessProcessors()
      .then((res) => {
        const items = Array.isArray(res?.data) ? res.data : [];
        setPostProcessors(items);
      })
      .catch(() => {
        setPostProcessors([]);
      });
  }, []);

  const enabledPostProcessors = useMemo(
    () => postProcessors.filter((row) => row.is_enabled),
    [postProcessors],
  );

  const demoCutoffLabel = useMemo(() => {
    const formatted = formatScanDate(demoScanCutoffDate);
    if (formatted) return formatted;
    const effective = formatScanDate(dataEnd?.effective_end_date);
    if (effective) return effective;
    return '—';
  }, [demoScanCutoffDate, dataEnd?.effective_end_date]);

  const refreshScanPrimaryActions = useCallback((options = {}) => {
    const silent = Boolean(options.silent);
    const demo = mode === 'demo';
    const list = Array.isArray(rows) ? rows.filter((r) => r?.name) : [];
    const reqId = readinessReqRef.current + 1;
    readinessReqRef.current = reqId;
    if (!silent) setReadinessLoading(true);
    setReadinessError('');

    if (list.length === 0) {
      if (readinessReqRef.current !== reqId) return;
      setScanPrimaryById({});
      setScanGateById({});
      setStrictBlockReason('');
      if (!silent) {
        setReadinessLoading(false);
      }
      return;
    }

    Promise.all(
      list.map((r) => fetchStrategyScanReadiness(r.name, { demo }).then((x) => ({
        id: r.id,
        action: x.primary_action === 'rerun' ? 'rerun' : 'run',
        report: x.report,
        canScan: x.can_scan === true,
        blockReason: String(x.block_reason || '').trim(),
      }))),
    )
      .then((pairs) => {
        if (readinessReqRef.current !== reqId) return;
        const next = {};
        const gates = {};
        let sharedBlock = '';
        pairs.forEach(({ id, action, canScan, blockReason }) => {
          next[id] = action;
          gates[id] = { canScan, blockReason };
          if (!demo && !sharedBlock && blockReason) sharedBlock = blockReason;
        });
        setScanPrimaryById(next);
        setScanGateById(gates);
        setStrictBlockReason(sharedBlock);
        setReadinessError('');
        if (sharedBlock) setRunError('');
        setResults((prev) => {
          const o = { ...(prev || {}) };
          pairs.forEach(({ id, action, report }) => {
            if (report && typeof report === 'object' && readOpportunityCount(report) != null) {
              o[id] = report;
            } else if (action === 'run') {
              // 未落盘才清空；保留内存中已确认的机会数（含合法 0），避免闪回「—」
              if (readOpportunityCount(o[id]) == null) delete o[id];
            }
          });
          return o;
        });
      })
      .catch(() => {
        if (readinessReqRef.current !== reqId) return;
        setScanPrimaryById({});
        setScanGateById({});
        setStrictBlockReason('');
        setReadinessError('无法读取扫描就绪状态，部分操作可能不可用。');
      })
      .finally(() => {
        if (readinessReqRef.current !== reqId) return;
        if (!silent) setReadinessLoading(false);
      });
  }, [rows, mode]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (loading) return undefined;
    refreshScanPrimaryActions();
    return undefined;
  }, [loading, refreshScanPrimaryActions]);

  useEffect(() => {
    selectedChipRef.current?.scrollIntoView({
      behavior: 'smooth',
      inline: 'nearest',
      block: 'nearest',
    });
  }, [categoryQuery]);

  useEffect(() => () => {
    if (pollRef.current.timeoutId) window.clearTimeout(pollRef.current.timeoutId);
  }, []);

  const openDetail = useCallback((strategyId) => {
    if (!strategyId) return;
    if (!results?.[strategyId]) return;
    setDetailStrategyId(strategyId);
    setDetailOpen(true);
  }, [results]);

  const closeDetail = () => {
    setDetailOpen(false);
    setDetailStrategyId('');
  };

  const columns = useMemo(() => ([
    {
      field: 'display_name',
      headerName: '策略',
      minWidth: 200,
      flex: 0.6,
      valueGetter: (params) => getStrategyDisplayLabel(params.row),
      renderCell: (params) => (
        <Stack spacing={0.5}>
          <Typography variant="body2" fontWeight={700}>
            {params.value || params.row.name}
          </Typography>
          <StrategyDescriptionText
            text={params.row.description}
            variant="caption"
            color="text.secondary"
            empty="—"
            maxLines={3}
          />
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
      headerAlign: 'center',
      align: 'center',
      renderCell: (params) => {
        const id = params.row.id;
        const enabled = Boolean(params.row.is_enabled);
        const pending = readinessLoading && scanPrimaryById[id] == null;
        const isThisRunning = running && id === runningStrategyId;
        if (pending || isThisRunning) {
          return <Typography variant="body2" color="text.secondary">…</Typography>;
        }
        const pack = results?.[id];
        if (!enabled || !pack) {
          return <Typography variant="body2" color="text.secondary">—</Typography>;
        }
        const n = readOpportunityCount(pack);
        if (n == null) {
          return <Typography variant="body2" color="text.secondary">—</Typography>;
        }
        return (
          <Button
            size="small"
            variant="text"
            className="scan-opp-count"
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
      headerName: '操作',
      width: 240,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const enabled = Boolean(params.row.is_enabled);
        const id = params.row.id;
        const pending = readinessLoading && scanPrimaryById[id] == null;
        const isThisRunning = running && id === runningStrategyId;
        const isRerun = scanPrimaryById[id] === 'rerun';
        const gate = scanGateById[id] || {};
        const blocked = mode === 'strict' && gate.canScan === false;
        const disableRun = pending || !enabled || running || blocked;
        return (
          <Stack direction="row" spacing={1} alignItems="center">
            {pending ? (
              <InlineLoadingState compact row message="校验中…" />
            ) : (
              <Button
                size="small"
                variant="contained"
                disabled={disableRun}
                startIcon={<NtqIcon name="play" size={16} />}
                title={
                  blocked
                    ? (gate.blockReason || '严格模式数据未就绪，无法扫描')
                    : (isRerun
                      ? '将全量重新扫描并忽略已保存的扫描结果'
                      : '尚无已保存结果时全量扫描；按住 Shift 再点击可强制重新扫描')
                }
                onClick={(e) => {
                  e.stopPropagation();
                  if (!enabled || running || blocked) return;
                  const force = isRerun || e.shiftKey;
                  setRunError('');
                  setReportVisible(false);
                  setReportStrategyId('');
                  setScanTriggeredAt(formatDateTime(new Date(), { style: 'absolute' }));
                  setProgress({ pct: 0, label: '准备扫描…' });
                  setResults((prev) => {
                    const next = { ...(prev || {}) };
                    delete next[id];
                    return next;
                  });
                  startStrategyScan(params.row.name, {
                    demo: mode === 'demo',
                    force,
                    runPostProcess,
                  })
                    .then((res) => {
                      const jobId = String(res?.job_id || '').trim();
                      if (!jobId) throw new Error('启动失败：未返回 job_id');
                      setRunningStrategyId(id);
                      setRunningJobId(jobId);
                      setReportDemo(Boolean(res?.demo));
                    })
                    .catch((err) => {
                      const msg = err?.message || '启动扫描失败';
                      // 严格门禁已有顶部提示时，不再重复打一条 error
                      if (mode === 'strict' && (gate.blockReason || msg.includes('严格模式'))) {
                        if (msg.includes('严格模式')) setStrictBlockReason(msg);
                        setRunError('');
                        return;
                      }
                      setRunError(msg);
                    });
                }}
              >
                {isRerun ? '重新扫描' : '开始扫描'}
              </Button>
            )}
            <Button
              size="small"
              variant="outlined"
              component={RouterLink}
              to={getStrategyDesignPath(params.row.name)}
              state={buildStrategyDesignNavState(params.row)}
              endIcon={<NtqIcon name="chevronRight" size={16} />}
              onClick={(e) => e.stopPropagation()}
              className="scan-design-btn"
            >
              调试策略
            </Button>
            {isThisRunning ? (
              <Typography variant="caption" color="text.secondary">
                {Math.round(progress.pct)}%
              </Typography>
            ) : null}
          </Stack>
        );
      },
    },
  ]), [mode, openDetail, progress.pct, readinessLoading, results, runPostProcess, running, runningStrategyId, scanGateById, scanPrimaryById]);

  useEffect(() => {
    if (!running) return undefined;
    const runningRow = rows.find((r) => r.id === runningStrategyId);
    const strategyName = runningRow?.name || '';
    if (!strategyName) return undefined;

    let cancelled = false;
    const pollSlot = pollRef.current;

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
            const report = p?.report && typeof p.report === 'object' ? p.report : null;
            // 仅在报告带明确机会数字段时写入，避免先闪「0」再跳到真实结果
            if (report && readOpportunityCount(report) != null) {
              setResults((prev) => ({ ...(prev || {}), [runningStrategyId]: report }));
            }
            setReportStrategyId(runningStrategyId);
            setReportStrategyName(getStrategyDisplayLabel(runningRow) || strategyName);
            setReportGeneratedAt(formatDateTime(new Date(), { style: 'absolute' }));
            if (typeof p?.demo === 'boolean') setReportDemo(p.demo);
            setReportVisible(true);
            setRunningStrategyId('');
            setRunningJobId('');
            window.setTimeout(() => {
              refreshScanPrimaryActions({ silent: true });
            }, 0);
            notifyTaskSuccess('scan');
            return;
          }
          if (status === 'failed') {
            setRunError(String(p?.reason || '扫描失败'));
            setRunningStrategyId('');
            setRunningJobId('');
            return;
          }

          pollSlot.timeoutId = window.setTimeout(pollOnce, 600);
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
      if (pollSlot.timeoutId) window.clearTimeout(pollSlot.timeoutId);
    };
  }, [mode, rows, running, runningJobId, runningStrategyId, refreshScanPrimaryActions]);

  return (
    <PageLayout
      className="scan-page"
      breadcrumbsItems={[{ label: '制定策略', to: '/strategy-design' }]}
      breadcrumbsCurrent="策略选股"
      bannerTitle="策略选股"
      bannerDescription={(
        <>
          勾选下方<strong>已启用</strong>的策略，在全市场范围内按规则筛选机会；每个策略按其配置的标的域（target）分别执行。
        </>
      )}
      bannerRightSlot={(
        <Chip
          label={
            running
              ? '扫描中…'
              : loading
                ? '加载中…'
                : readinessLoading
                  ? '校验就绪…'
                  : '就绪'
          }
          color={running ? 'warning' : 'default'}
          variant={running || loading || readinessLoading ? 'filled' : 'outlined'}
        />
      )}
      loading={!pageReady}
      loadingMessage="正在加载策略选股…"
    >

      <SectionBlock className="scan-section scan-section--compact">
        <Box className="scan-settings">
          <Box className="scan-settings__modes">
            <Typography variant="subtitle1" className="scan-settings__label">
              扫描模式
            </Typography>
            <FormControl component="fieldset" disabled={running} fullWidth>
              <RadioGroup
                value={mode}
                onChange={(e) => {
                  setMode(e.target.value);
                  setRunError('');
                  setStrictBlockReason('');
                  setScanPrimaryById({});
                  setScanGateById({});
                  setReadinessLoading(true);
                }}
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
                        依赖数据须更新至<strong>最新交易日</strong>，否则中断并提示缺口。
                      </Typography>
                    </Box>
                  )}
                  className={[
                    'scan-mode-option',
                    mode === 'strict' ? 'scan-mode-option--active' : '',
                    running ? 'scan-mode-option--disabled' : '',
                  ].filter(Boolean).join(' ')}
                />
                <FormControlLabel
                  value="demo"
                  control={<Radio disabled={running} />}
                  label={(
                    <Box className="scan-mode-option-body">
                      <Typography variant="body2" fontWeight={700}>扫描演示</Typography>
                      <Typography variant="body2" color="text.secondary">
                        截止
                        {' '}
                        <strong>{contextLoading ? '…' : demoCutoffLabel}</strong>
                        {!contextLoading && dataEnd.is_end_date_truncated ? '（受会员档约束）' : ''}
                        ，演示用，非实时市场。
                      </Typography>
                    </Box>
                  )}
                  className={[
                    'scan-mode-option',
                    mode === 'demo' ? 'scan-mode-option--active' : '',
                    running ? 'scan-mode-option--disabled' : '',
                  ].filter(Boolean).join(' ')}
                />
              </RadioGroup>
            </FormControl>
          </Box>

          <Box className="scan-settings__divider" aria-hidden />

          <Box className="scan-settings__post">
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              spacing={1}
              className="scan-settings__post-head"
            >
              <Typography variant="subtitle1" className="scan-settings__label">
                扫描后处理
              </Typography>
              <FormControlLabel
                className="scan-settings__pp-switch"
                control={(
                  <Switch
                    size="small"
                    checked={runPostProcess && enabledPostProcessors.length > 0}
                    disabled={running || enabledPostProcessors.length === 0}
                    onChange={(e) => {
                      const next = e.target.checked;
                      const prev = runPostProcess;
                      setRunPostProcess(next);
                      setPostProcessRunEnabled({ enablePostProcess: next })
                        .then((res) => {
                          setRunPostProcess(res?.enablePostProcess !== false);
                        })
                        .catch(() => {
                          setRunPostProcess(prev);
                          setRunError('无法保存「执行扫描后处理」偏好');
                        });
                    }}
                    inputProps={{ 'aria-label': '执行扫描后处理' }}
                  />
                )}
                label={(
                  <Typography variant="caption" color="text.secondary">
                    执行扫描后处理
                  </Typography>
                )}
                labelPlacement="start"
              />
            </Stack>
            <Typography variant="body2" color="text.secondary" className="scan-settings__post-hint">
              默认开启；关闭会写入工作区偏好并跳过扫描后处理（可能产生费用），不改全局方案启用。
            </Typography>
            {enabledPostProcessors.length ? (
              <Stack
                direction="row"
                spacing={0.75}
                flexWrap="wrap"
                useFlexGap
                className={[
                  'scan-settings__chips',
                  !runPostProcess ? 'scan-settings__chips--muted' : '',
                ].filter(Boolean).join(' ')}
              >
                {enabledPostProcessors.map((row) => (
                  <Chip
                    key={row.key}
                    size="small"
                    label={row.name || row.key}
                    variant="outlined"
                  />
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                当前未启用任何扫描后处理方案。
              </Typography>
            )}
            <Box className="scan-settings__post-actions">
              <Button
                size="small"
                variant="outlined"
                component={RouterLink}
                to="/advanced/post-process"
                endIcon={<NtqIcon name="chevronRight" size={16} />}
                className="scan-design-btn"
              >
                管理扫描后处理
              </Button>
            </Box>
          </Box>
        </Box>
      </SectionBlock>

      <SectionBlock className="scan-section">
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            alignItems={{ xs: 'stretch', sm: 'center' }}
            spacing={1.5}
            className="scan-toolbar"
          >
            <SearchField
              placeholder="输入策略名称搜索"
              label="按策略名搜索"
              value={nameQuery}
              onChange={(e) => setNameQuery(e.target.value)}
            />
            <Button
              variant="outlined"
              disabled={running || loading}
              onClick={load}
            >
              刷新策略列表
            </Button>
            <Typography variant="caption" color="text.secondary" className="scan-toolbar__hint">
              一次仅允许扫描一个策略；运行中会禁用其它策略的扫描按钮。
            </Typography>
          </Stack>

          {catalogGroups.length > 0 ? (
            <Stack
              direction="row"
              alignItems="center"
              className="scan-category-chips"
              role="group"
              aria-label="按归类筛选"
            >
              <CountTab
                wide
                label="全部"
                count={rows.length}
                selected={!categoryQuery}
                onClick={() => setCategoryQuery('')}
              />
              <Box className="scan-category-chips-scroller">
                {catalogGroups.map(({ category, queryValue, rows: categoryRows }) => {
                  const selected = categoryQuery === queryValue;
                  return (
                    <CountTab
                      key={queryValue}
                      label={category}
                      count={categoryRows.length}
                      title={category}
                      selected={selected}
                      ref={selected ? selectedChipRef : undefined}
                      onClick={() => toggleCategoryQuery(queryValue)}
                    />
                  );
                })}
              </Box>
            </Stack>
          ) : null}

          {loadError ? <Message severity="error" className="scan-alert">{loadError}</Message> : null}
          {readinessError ? (
            <Message severity="warning" className="scan-alert" onClose={() => setReadinessError('')}>
              {readinessError}
            </Message>
          ) : null}
          <DataEndTruncationAlert dataEnd={dataEnd} className="scan-list-alert" />
          {!readinessLoading && mode === 'strict' && strictBlockReason ? (
            <Message severity="warning" className="scan-alert">
              {strictBlockReason}
            </Message>
          ) : null}
          {runError && runError !== strictBlockReason ? (
            <Message severity="error" className="scan-alert">{runError}</Message>
          ) : null}

          {running ? (
            <div className="scan-progress">
              <div className="scan-progress-row">
                <div className="scan-progress__bar">
                  <LinearProgress variant="determinate" value={progress.pct} />
                </div>
                <Typography variant="caption" color="text.secondary" className="scan-progress-label">
                  {progress.label}
                </Typography>
              </div>
            </div>
          ) : null}

          <Box className={['scan-strategy-list', loading && rows.length === 0 ? 'scan-strategy-list--loading' : ''].filter(Boolean).join(' ')}>
            {loading && rows.length === 0 ? (
              <InlineLoadingState
                block
                compact
                message="正在加载策略列表…"
              />
            ) : !loading && categoryQuery && !catalogHasSelectedCategory ? (
              <Typography variant="body2" color="text.secondary" className="scan-category-empty">
                没有该归类的策略
              </Typography>
            ) : groupedRows.length === 0 ? (
              <Typography variant="body2" color="text.secondary" className="scan-category-empty">
                {nameQuery.trim() ? '没有匹配的策略' : '暂无策略'}
              </Typography>
            ) : (
              <Stack spacing={2.5}>
                {groupedRows.map(({ category, queryValue, rows: categoryRows }) => (
                  <Box key={queryValue} className="scan-category-section">
                    <Stack direction="row" alignItems="center" spacing={1} className="scan-category">
                      <Box
                        component="button"
                        type="button"
                        className="scan-category-header-btn"
                        onClick={() => toggleCategoryQuery(queryValue)}
                        aria-pressed={categoryQuery === queryValue}
                        title={categoryQuery === queryValue ? '显示全部归类' : `只看${category}`}
                      >
                        <Typography
                          variant="subtitle1"
                          fontWeight={700}
                          component="span"
                          className="scan-category-header-label"
                        >
                          {category}
                        </Typography>
                        <CountBadge
                          count={categoryRows.length}
                          label={`${categoryRows.length} 个策略`}
                        />
                      </Box>
                    </Stack>
                    <DataGrid
                      autoHeight
                      rows={categoryRows}
                      columns={columns}
                      loading={false}
                      getRowHeight={() => 'auto'}
                      slots={NTQ_DATA_GRID_LOADING_SLOTS}
                      localeText={zhCN}
                      hideFooter
                      disableRowSelectionOnClick
                      className="scan-strategy-grid"
                    />
                  </Box>
                ))}
              </Stack>
            )}
          </Box>
      </SectionBlock>

      {reportVisible ? (
      <SectionBlock
        title="扫描报告"
        action={(
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
        )}
      >
            <>
              <Typography variant="body2" className="scan-report__lead">
                使用策略
                {' '}
                <strong>{reportStrategyName || reportStrategyId || '—'}</strong>
                {' '}
                扫描完成：共找到
                {' '}
                {(() => {
                  const reportCount = readOpportunityCount(reportPayload);
                  return (
                    <Button
                      size="small"
                      variant="text"
                      className="scan-report__count"
                      disabled={reportCount == null}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!reportStrategyId || reportCount == null) return;
                        openDetail(reportStrategyId);
                      }}
                    >
                      {reportCount == null ? '—' : reportCount}
                    </Button>
                  );
                })()}
                {' '}
                个机会
              </Typography>
              <div className="scan-report__facts">
                <Typography variant="body2" color="text.secondary" className="scan-report__fact">
                  - 扫描日期：{formatScanDate(reportPayload?.date) || '—'}
                </Typography>
                <Typography variant="body2" color="text.secondary" className="scan-report__fact">
                  - 总扫描股票数：{Number(reportPayload?.total_stocks ?? 0) || '—'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  - 模式：{reportDemo === true ? '演示模式' : '严格模式'}
                </Typography>
                <Typography variant="body2" color="text.secondary" className="scan-report__fact">
                  - 扫描后处理：{(() => {
                    if (reportPayload?.post_process?.skipped) return '本次已跳过';
                    const ran = Array.isArray(reportPayload?.post_process?.ran)
                      ? reportPayload.post_process.ran
                      : [];
                    const enabled = Array.isArray(reportPayload?.post_process?.enabled)
                      ? reportPayload.post_process.enabled
                      : enabledPostProcessors.map((row) => row.key);
                    if (ran.length) return `已运行 ${ran.join('、')}`;
                    if (enabled.length) return '已启用但未回报运行结果（可能失败或跳过）';
                    return '未启用';
                  })()}
                </Typography>
              </div>
              <Typography variant="caption" color="text.secondary" className="scan-report__hint">
                请点击表格里的机会数量查看详情。
              </Typography>
            </>
      </SectionBlock>
      ) : null}

      <Dialog
        open={detailOpen}
        onClose={closeDetail}
        maxWidth={detailPresenterUi ? 'lg' : 'md'}
        fullWidth
        className="scan-detail-dialog"
      >
        <DialogTitle className="scan-detail__title">机会明细</DialogTitle>
        <DialogContent dividers className="scan-detail__body">
          {detailPayload ? (
            <>
              <OpportunityDetailMeta
                strategyName={detailStrategyName}
                scanDate={detailPayload?.date || detailPayload?.scan_date}
                opportunityCount={(() => {
                  const n = readOpportunityCount(detailPayload);
                  if (n != null) return n;
                  const ops = detailPayload?.opportunities;
                  return Array.isArray(ops) ? ops.length : null;
                })()}
                presenterLine={
                  detailPresenterUi && !detailPresenterHistory.error
                    ? (formatSessionSummaryLine(detailPresenterHistory.sessionSummary)
                      || '（无 price 层 overall_report / 尚未回测）')
                    : ''
                }
                presenterError={
                  detailPresenterUi ? detailPresenterHistory.error : ''
                }
              />
              <Box className="scan-detail__grid">
                <DataGrid
                  rows={(() => {
                    const byStock = detailPresenterUi ? detailPresenterHistory.byStock : {};
                    const ops = Array.isArray(detailPayload?.opportunities)
                      ? detailPayload.opportunities
                      : null;
                    if (ops) {
                      return ops.map((o, idx) => mapOpportunityRow(o, idx, byStock));
                    }
                    const list = Array.isArray(detailPayload?.summary?.stocks_with_opportunities)
                      ? detailPayload.summary.stocks_with_opportunities
                      : [];
                    return list.map((code, idx) => mapOpportunityRow(
                      { stock_id: code },
                      idx,
                      byStock,
                    ));
                  })()}
                  columns={buildOpportunityColumns({ withPresenter: Boolean(detailPresenterUi) })}
                  getRowHeight={() => 'auto'}
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

export default Scan;

