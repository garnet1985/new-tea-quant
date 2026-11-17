import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import {
  Button,
  CountBadge,
  CountTab,
  DataGrid,
  Dialog,
  Heading,
  Loading,
  Message,
  ProgressBar,
  RadioGroup,
  SearchField,
  Section,
  Switch,
  Tag,
} from 'ui';
import { PageLayout } from 'ntq-ui';
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
import DataEndTruncationAlert from '../../views/dataEndTruncationAlert';
import StrategyDescriptionText from '../../views/strategyDescriptionText';
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
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
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

  const [results, setResults] = useState({});
  const [postProcessors, setPostProcessors] = useState([]);
  const [runPostProcess, setRunPostProcess] = useState(true);
  const [reportVisible, setReportVisible] = useState(false);
  const [reportStrategyId, setReportStrategyId] = useState('');
  const [reportStrategyName, setReportStrategyName] = useState('');
  const [scanTriggeredAt, setScanTriggeredAt] = useState('');
  const [reportGeneratedAt, setReportGeneratedAt] = useState('');
  const [reportDemo, setReportDemo] = useState(null);

  const [scanPrimaryById, setScanPrimaryById] = useState({});
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
      if (!silent) setReadinessLoading(false);
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
        <div className="scan-cell-strategy">
          <span className="scan-cell-strategy__name">
            {params.value || params.row.name}
          </span>
          <StrategyDescriptionText
            text={params.row.description}
            className="scan-cell-strategy__desc ntq-muted"
            empty="—"
            maxLines={3}
          />
        </div>
      ),
    },
    {
      field: 'is_enabled',
      headerName: '启用',
      width: 110,
      renderCell: (params) => (params.value ? (
        <Tag status="success" variant="solid">已启用</Tag>
      ) : (
        <Tag status="neutral" variant="outline">已禁用</Tag>
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
          return <span className="ntq-muted">…</span>;
        }
        const pack = results?.[id];
        if (!enabled || !pack) {
          return <span className="ntq-muted">—</span>;
        }
        const n = readOpportunityCount(pack);
        if (n == null) {
          return <span className="ntq-muted">—</span>;
        }
        return (
          <Button
            variant="ghost"
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
      width: 260,
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
          <div className="scan-cell-actions">
            {pending ? (
              <Loading variant="inlineRow" message="校验中…" className="scan-cell-actions__loading" />
            ) : (
              <Button
                variant="primary"
                icon="play"
                iconSize="sm"
                disabled={disableRun}
                tooltip={
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
              variant="glass"
              icon="chevronRight"
              iconPlacement="end"
              iconSize="sm"
              component={RouterLink}
              to={getStrategyDesignPath(params.row.name)}
              state={buildStrategyDesignNavState(params.row)}
              onClick={(e) => e.stopPropagation()}
              className="scan-design-btn"
            >
              调试策略
            </Button>
            {isThisRunning ? (
              <span className="ntq-muted scan-cell-actions__pct">
                {Math.round(progress.pct)}%
              </span>
            ) : null}
          </div>
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

  const statusTag = running
    ? { label: '扫描中…', status: 'warning', variant: 'solid' }
    : loading
      ? { label: '加载中…', status: 'neutral', variant: 'outline' }
      : readinessLoading
        ? { label: '校验就绪…', status: 'neutral', variant: 'outline' }
        : { label: '就绪', status: 'success', variant: 'solid' };

  const demoDesc = contextLoading
    ? '截止 …'
    : `截止 ${demoCutoffLabel}${dataEnd.is_end_date_truncated ? '（受会员档约束）' : ''}，演示用，非实时市场。`;

  const reportCount = readOpportunityCount(reportPayload);

  return (
    <PageLayout
      className="scan-page"
      breadcrumbsItems={[{ label: '制定策略', to: '/strategy-design' }]}
      breadcrumbsCurrent="策略选股"
      bannerTitle="策略选股"
      bannerDescription="勾选下方已启用的策略，在全市场范围内按规则筛选机会；每个策略按其配置的标的域（target）分别执行。"
      bannerRightSlot={(
        <Tag status={statusTag.status} variant={statusTag.variant}>
          {statusTag.label}
        </Tag>
      )}
      loading={!pageReady}
      loadingMessage="正在加载策略选股…"
    >
      <Section className="scan-page__stack" gap="md">
        {/* —— Landing：扫描设置 —— */}
        <Section className="scan-section scan-section--settings" gap="none">
          <div className="scan-settings">
            <div className="scan-settings__modes">
              <RadioGroup
                label="扫描模式"
                variant="button"
                direction="row"
                value={mode}
                disabled={running}
                className="scan-mode-options"
                onChange={(e) => {
                  setMode(e.target.value);
                  setRunError('');
                  setStrictBlockReason('');
                  setScanPrimaryById({});
                  setScanGateById({});
                  setReadinessLoading(true);
                }}
                options={[
                  {
                    value: 'strict',
                    label: '严格模式',
                    description: '依赖数据须更新至最新交易日，否则中断并提示缺口。',
                  },
                  {
                    value: 'demo',
                    label: '扫描演示',
                    description: demoDesc,
                  },
                ]}
              />
            </div>

            <div className="scan-settings__divider" aria-hidden />

            <div className="scan-settings__post">
              <div className="scan-settings__post-head">
                <Heading level="h4" gap="none" className="scan-settings__label">
                  扫描后处理
                </Heading>
                <Switch
                  label="执行扫描后处理"
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
                  aria-label="执行扫描后处理"
                />
              </div>
              <p className="ntq-muted scan-settings__post-hint">
                默认开启；关闭会写入工作区偏好并跳过扫描后处理（可能产生费用），不改全局方案启用。
              </p>
              {enabledPostProcessors.length ? (
                <div
                  className={[
                    'scan-settings__chips',
                    !runPostProcess ? 'scan-settings__chips--muted' : '',
                  ].filter(Boolean).join(' ')}
                >
                  {enabledPostProcessors.map((row) => (
                    <Tag key={row.key} status="neutral" variant="solid">
                      {row.name || row.key}
                    </Tag>
                  ))}
                </div>
              ) : (
                <p className="ntq-muted">当前未启用任何扫描后处理方案。</p>
              )}
              <div className="scan-settings__post-actions">
                <Button
                  variant="glass"
                  icon="chevronRight"
                  iconPlacement="end"
                  iconSize="sm"
                  component={RouterLink}
                  to="/advanced/post-process"
                  className="scan-design-btn"
                >
                  管理扫描后处理
                </Button>
              </div>
            </div>
          </div>
        </Section>

        {/* —— Landing：策略列表 —— */}
        <Section className="scan-section scan-section--list" gap="md">
          <div className="scan-toolbar">
            <SearchField
              fluid
              surface="glass"
              placeholder="输入策略名称搜索"
              label="按策略名搜索"
              value={nameQuery}
              onChange={(e) => setNameQuery(e.target.value)}
            />
            <Button
              variant="glass"
              icon="refresh"
              disabled={running || loading}
              onClick={load}
            >
              刷新策略列表
            </Button>
            <span className="ntq-muted scan-toolbar__hint">
              一次仅允许扫描一个策略；运行中会禁用其它策略的扫描按钮。
            </span>
          </div>

          {catalogGroups.length > 0 ? (
            <div
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
              <div className="scan-category-chips-scroller">
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
              </div>
            </div>
          ) : null}

          {loadError ? <Message status="error">{loadError}</Message> : null}
          {readinessError ? (
            <Message status="warning" onClose={() => setReadinessError('')}>
              {readinessError}
            </Message>
          ) : null}
          <DataEndTruncationAlert dataEnd={dataEnd} />
          {!readinessLoading && mode === 'strict' && strictBlockReason ? (
            <Message status="warning">{strictBlockReason}</Message>
          ) : null}
          {runError && runError !== strictBlockReason ? (
            <Message status="error">{runError}</Message>
          ) : null}

          {running ? (
            <ProgressBar
              className="scan-progress"
              size="md"
              value={progress.pct}
              label={progress.label}
              showPercent
            />
          ) : null}

          <div className={[
            'scan-strategy-list',
            loading && rows.length === 0 ? 'scan-strategy-list--loading' : '',
          ].filter(Boolean).join(' ')}
          >
            {loading && rows.length === 0 ? (
              <Loading variant="inline" message="正在加载策略列表…" />
            ) : !loading && categoryQuery && !catalogHasSelectedCategory ? (
              <p className="ntq-muted scan-category-empty">没有该归类的策略</p>
            ) : groupedRows.length === 0 ? (
              <p className="ntq-muted scan-category-empty">
                {nameQuery.trim() ? '没有匹配的策略' : '暂无策略'}
              </p>
            ) : (
              <div className="scan-category-stack">
                {groupedRows.map(({ category, queryValue, rows: categoryRows }) => (
                  <div key={queryValue} className="scan-category-section">
                    <div className="scan-category">
                      <button
                        type="button"
                        className="scan-category-header-btn"
                        onClick={() => toggleCategoryQuery(queryValue)}
                        aria-pressed={categoryQuery === queryValue}
                        title={categoryQuery === queryValue ? '显示全部归类' : `只看${category}`}
                      >
                        <span className="scan-category-header-label">{category}</span>
                        <CountBadge
                          count={categoryRows.length}
                          label={`${categoryRows.length} 个策略`}
                        />
                      </button>
                    </div>
                    <DataGrid
                      autoHeight
                      rows={categoryRows}
                      columns={columns}
                      loading={false}
                      getRowHeight={() => 'auto'}
                      hideFooter
                      className="scan-strategy-grid"
                      sx={{
                        '& .MuiDataGrid-cell': {
                          py: 1.25,
                          alignItems: 'flex-start',
                          whiteSpace: 'normal',
                          lineHeight: 1.5,
                        },
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </Section>

        {/* 报告 / 明细下一轮再细抠；本轮先换成 ui 外壳，保证 landing 可跑通 */}
        {reportVisible ? (
          <Section className="scan-section scan-section--report" gap="sm">
            <div className="scan-report__head">
              <Heading level="h3" gap="none">扫描报告</Heading>
              <span className="ntq-muted">
                扫描当日：{scanTriggeredAt || reportGeneratedAt || '—'}
              </span>
              {SHOW_REPORT_GENERATED_AT ? (
                <span className="ntq-muted">报告日期：{reportGeneratedAt || '—'}</span>
              ) : null}
            </div>
            <p className="scan-report__lead">
              使用策略
              {' '}
              <strong>{reportStrategyName || reportStrategyId || '—'}</strong>
              {' '}
              扫描完成：共找到
              {' '}
              <Button
                variant="ghost"
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
              {' '}
              个机会
            </p>
            <div className="scan-report__facts ntq-muted">
              <p>- 扫描日期：{formatScanDate(reportPayload?.date) || '—'}</p>
              <p>- 总扫描股票数：{Number(reportPayload?.total_stocks ?? 0) || '—'}</p>
              <p>- 模式：{reportDemo === true ? '演示模式' : '严格模式'}</p>
              <p>
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
              </p>
            </div>
            <p className="ntq-muted scan-report__hint">请点击表格里的机会数量查看详情。</p>
          </Section>
        ) : null}
      </Section>

      <Dialog
        open={detailOpen}
        onClose={closeDetail}
        title="机会明细"
        size="lg"
        maxWidth={detailPresenterUi ? 'lg' : 'md'}
        className="scan-detail-dialog"
        actions={<Button variant="glass" onClick={closeDetail}>关闭</Button>}
      >
        <div className="scan-detail__body">
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
              <div className="scan-detail__grid">
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
                  pageSizeOptions={[10, 25, 50]}
                  initialState={{
                    pagination: { paginationModel: { page: 0, pageSize: 10 } },
                  }}
                />
              </div>
            </>
          ) : (
            <p className="ntq-muted">暂无明细。</p>
          )}
        </div>
      </Dialog>
    </PageLayout>
  );
}

export default Scan;
