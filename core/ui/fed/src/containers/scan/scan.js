import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import {
  Button,
  Loading,
  Section,
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
import DescriptionText from 'ntq-ui/descriptionText';
import { buildStrategyDesignNavState } from 'containers/strategyDesign';
import { notifyTaskSuccess } from '../../service/feedbackPromptBus';
import { formatDateTime } from '../../service/format/formatDateTime';
import { readPresenterHistory, readPresenterScanUi } from './presenterScanReport';
import { formatScanDate, readOpportunityCount } from './scanHelpers';
import ScanSettingsSection from './scanSettingsSection';
import ScanStrategyListSection from './scanStrategyListSection';
import ScanReportSection from './scanReportSection';
import ScanDetailDialog from './scanDetailDialog';
import './style.scss';

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
          <DescriptionText
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
          <div className="scan-cell-actions" data-ntq-help="scan-start">
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
        <ScanSettingsSection
          mode={mode}
          running={running}
          demoDesc={demoDesc}
          runPostProcess={runPostProcess}
          enabledPostProcessors={enabledPostProcessors}
          onModeChange={(e) => {
            setMode(e.target.value);
            setRunError('');
            setStrictBlockReason('');
            setScanPrimaryById({});
            setScanGateById({});
            setReadinessLoading(true);
          }}
          onRunPostProcessChange={(e) => {
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
        />

        <ScanStrategyListSection
          nameQuery={nameQuery}
          onNameQueryChange={(e) => setNameQuery(e.target.value)}
          running={running}
          loading={loading}
          onRefresh={load}
          catalogGroups={catalogGroups}
          rows={rows}
          categoryQuery={categoryQuery}
          setCategoryQuery={setCategoryQuery}
          toggleCategoryQuery={toggleCategoryQuery}
          selectedChipRef={selectedChipRef}
          loadError={loadError}
          readinessError={readinessError}
          onClearReadinessError={() => setReadinessError('')}
          dataEnd={dataEnd}
          readinessLoading={readinessLoading}
          mode={mode}
          strictBlockReason={strictBlockReason}
          runError={runError}
          progress={progress}
          catalogHasSelectedCategory={catalogHasSelectedCategory}
          groupedRows={groupedRows}
          columns={columns}
        />

        {reportVisible ? (
          <ScanReportSection
            scanTriggeredAt={scanTriggeredAt}
            reportGeneratedAt={reportGeneratedAt}
            reportStrategyName={reportStrategyName}
            reportStrategyId={reportStrategyId}
            reportCount={reportCount}
            onOpenDetail={openDetail}
            reportPayload={reportPayload}
            reportDemo={reportDemo}
            enabledPostProcessors={enabledPostProcessors}
          />
        ) : null}
      </Section>

      <ScanDetailDialog
        open={detailOpen}
        onClose={closeDetail}
        detailPresenterUi={detailPresenterUi}
        detailPayload={detailPayload}
        detailStrategyName={detailStrategyName}
        detailPresenterHistory={detailPresenterHistory}
      />
    </PageLayout>
  );
}

export default Scan;
