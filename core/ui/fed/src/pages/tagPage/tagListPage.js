import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  DataGrid,
  HelpTooltip,
  Icon,
  Message,
  SearchField,
  Section,
  Tag,
} from 'ui';
import { GridRow } from 'ui/table/dataGrid';
import { TAG_COLORS } from 'ui/tokens';
import { PageLayout, RainbowButton } from 'ntq-ui';
import { showToast } from 'ui/message/toast';
import {
  fetchPipelineStatus,
  fetchTagList,
  fetchTagRunProgress,
  formatTagAsOfDate,
  getTagComputeStatusLabel,
  getTagDisplayLabel,
  getTagUpdateModeIcon,
  getTagUpdateModeLabel,
  startTagRun,
} from '../../api/tagApi';
import DataEndTruncationAlert from '../../views/dataEndTruncationAlert';
import StrategyDescriptionText from '../../views/strategyDescriptionText';
import FreshnessStatusChip from '../../views/freshnessStatusChip';
import { notifyTaskSuccess } from '../../service/feedbackPromptBus';
import TagVisualization from '../../containers/tagVisualization';
import './tagListPage.scss';

/** 按名称稳定散列到装饰色（同名同色，刷新不跳） */
function tagColorFromName(name) {
  const palette = TAG_COLORS.filter((c) => c !== 'muted');
  const s = String(name || '');
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return palette[h % palette.length] || 'cyan';
}

function clearRowProgress(rows) {
  return rows.map((row) => {
    if (!row.__progress) return row;
    const next = { ...row };
    delete next.__progress;
    return next;
  });
}

function ComputeStatusChip({ row }) {
  return (
    <FreshnessStatusChip
      status={row.compute_status}
      label={getTagComputeStatusLabel(row)}
      hint={row.compute_status_hint}
    />
  );
}

function TagListPage() {
  const [rows, setRows] = useState([]);
  const [dataEnd, setDataEnd] = useState({});
  const [loading, setLoading] = useState(true);
  const [pageReady, setPageReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 10 });

  const [pipelineBusy, setPipelineBusy] = useState(false);
  const [pipelineLabel, setPipelineLabel] = useState('');
  const [pipelineError, setPipelineError] = useState('');

  const [runningTagId, setRunningTagId] = useState('');
  const [runningTagKey, setRunningTagKey] = useState('');
  const [runningJobId, setRunningJobId] = useState('');
  const [vizTarget, setVizTarget] = useState(null);

  const pollRef = useRef({ timeoutId: null });
  const runningTagIdRef = useRef('');
  runningTagIdRef.current = runningTagId;
  const running = Boolean(runningTagId) && Boolean(runningJobId);

  const TagListGridRow = useCallback((rowProps) => {
    const progress = rowProps.row.__progress;
    const isRunning = Boolean(progress) || rowProps.rowId === runningTagIdRef.current;
    const pct = Number(progress?.pct ?? 0);
    const safePct = Number.isFinite(pct) ? Math.max(0, Math.min(100, pct)) : 0;
    const extraClasses = [
      isRunning ? 'tag-list-row--running' : '',
      isRunning && safePct <= 0 ? 'tag-list-row--running-indeterminate' : '',
    ].filter(Boolean).join(' ');

    return (
      <GridRow
        {...rowProps}
        className={[rowProps.className, extraClasses].filter(Boolean).join(' ')}
        style={{
          ...rowProps.style,
          ...(isRunning ? { '--tag-run-pct': `${safePct}%` } : undefined),
        }}
      />
    );
  }, []);

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const id = String(r.name || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
      const desc = String(r.description || '').toLowerCase();
      const tags = (r.tag_definitions || [])
        .map((t) => `${t.display_name || ''} ${t.name || ''}`.toLowerCase())
        .join(' ');
      return id.includes(q) || label.includes(q) || desc.includes(q) || tags.includes(q);
    });
  }, [rows, nameQuery]);

  const refreshPipeline = useCallback(() => {
    fetchPipelineStatus()
      .then((st) => {
        setPipelineBusy(Boolean(st.busy) && st.kind !== 'tag_run');
        setPipelineLabel(String(st.label || st.kind || '').trim());
        setPipelineError('');
      })
      .catch(() => {
        setPipelineBusy(false);
        setPipelineLabel('');
        setPipelineError('无法读取数据管道状态，运行按钮可能不准确。');
      });
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchTagList({ page: 1, limit: 200 })
      .then((res) => {
        setRows(clearRowProgress(Array.isArray(res?.data) ? res.data : []));
        setDataEnd(res?.dataEnd && typeof res.dataEnd === 'object' ? res.dataEnd : {});
      })
      .catch((e) => {
        setRows([]);
        setDataEnd({});
        setLoadError(e?.message || '加载 Tag 列表失败');
      })
      .finally(() => {
        setLoading(false);
        setPageReady(true);
      });
    refreshPipeline();
  }, [refreshPipeline]);

  const patchRunningRowProgress = useCallback((tagId, patch) => {
    setRows((prev) => prev.map((row) => {
      if (row.id !== tagId) {
        return row.__progress ? { ...row, __progress: undefined } : row;
      }
      return { ...row, __progress: patch };
    }));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPaginationModel((m) => ({ ...m, page: 0 }));
  }, [nameQuery]);

  useEffect(() => () => {
    if (pollRef.current.timeoutId) window.clearTimeout(pollRef.current.timeoutId);
  }, []);

  const columns = useMemo(() => ([
    {
      field: 'display_name',
      headerName: '场景',
      minWidth: 140,
      flex: 0.4,
      valueGetter: (params) => getTagDisplayLabel(params.row),
      renderCell: (params) => {
        const label = params.value || params.row.name;
        const description = String(params.row.description || '').trim();
        return (
          <div className="tag-list-cell-name">
            <strong className="tag-list-cell-name__label">{label}</strong>
            {description ? (
              <HelpTooltip
                title={(
                  <StrategyDescriptionText
                    text={description}
                    empty=""
                  />
                )}
                ariaLabel={`${label} 简介`}
              />
            ) : null}
          </div>
        );
      },
    },
    {
      field: 'is_enabled',
      headerName: '启用状态',
      width: 110,
      renderCell: (params) => (params.value ? (
        <Tag status="success" variant="solid">已启用</Tag>
      ) : (
        <Tag status="neutral" variant="outline">已禁用</Tag>
      )),
    },
    {
      field: 'actions',
      headerName: '操作',
      width: 72,
      sortable: false,
      filterable: false,
      cellClassName: 'tag-list-cell--actions',
      renderCell: (params) => {
        const enabled = Boolean(params.row.is_enabled);
        const id = params.row.id;
        const isThisRunning = id === runningTagId;
        const disableRun = !enabled || Boolean(runningTagId);
        let title = '';
        if (!enabled) title = 'Scenario 未启用';
        else if (running && !isThisRunning) title = '已有 Tag 任务在运行';
        else if (pipelineBusy) title = pipelineLabel ? `系统忙时可加入队列：${pipelineLabel}` : '系统忙时可加入队列';
        else title = '运行 Tag 计算';

        return (
          <span className="tag-list-run-btn-wrap" title={title}>
            <RainbowButton
              icon="play"
              disabled={disableRun}
              aria-label={pipelineBusy && !running ? '加入队列' : '运行 Tag 计算'}
              onClick={(e) => {
                e.stopPropagation();
                setRunningTagId(id);
                setRunningTagKey(params.row.name);
                setRunningJobId('');
                patchRunningRowProgress(id, { pct: 0, label: pipelineBusy ? '加入队列…' : '准备中…' });
                startTagRun(params.row.name)
                  .then((res) => {
                    if (res?.queued) {
                      showToast({
                        status: 'info',
                        duration: 5000,
                        content: res.reason || '已加入管道队列，当前任务结束后将自动执行',
                      });
                      setRunningTagId('');
                      setRunningTagKey('');
                      setRunningJobId('');
                      setRows((prev) => clearRowProgress(prev));
                      refreshPipeline();
                      return;
                    }
                    const jobId = String(res?.job_id || '').trim();
                    if (!jobId) throw new Error('启动失败：未返回 job_id');
                    setRunningTagId(id);
                    setRunningJobId(jobId);
                  })
                  .catch((err) => {
                    showToast({ status: 'error', content: err?.message || '启动 Tag 计算失败' });
                    setRunningTagId('');
                    setRunningTagKey('');
                    setRunningJobId('');
                    setRows((prev) => clearRowProgress(prev));
                    refreshPipeline();
                  });
              }}
            />
          </span>
        );
      },
    },
    {
      field: 'visualize',
      headerName: '可视化',
      width: 88,
      sortable: false,
      filterable: false,
      align: 'center',
      headerAlign: 'center',
      cellClassName: 'tag-list-cell--actions',
      renderCell: (params) => {
        const computed = Boolean(String(params.row.last_computed_as_of || '').trim());
        const title = computed ? '打开标签可视化' : '尚未计算，无法可视化';
        return (
          <span className="tag-list-run-btn-wrap">
            <Button
              variant="glass"
              icon="monitoring"
              iconSize="sm"
              disabled={!computed}
              className="tag-list-viz-btn"
              tooltip={title}
              aria-label={title}
              onClick={(event) => {
                event.stopPropagation();
                if (!computed) return;
                setVizTarget({
                  name: params.row.name,
                  display_name: params.row.display_name,
                });
              }}
            />
          </span>
        );
      },
    },
    {
      field: 'update_mode',
      headerName: '更新方式',
      width: 110,
      renderCell: (params) => {
        // 样式对齐数据源列表：青色 Icon + 文案（非 Tag 胶囊）
        const label = getTagUpdateModeLabel(params.row.update_mode);
        const iconName = getTagUpdateModeIcon(params.row.update_mode);
        return (
          <div className="tag-list-cell-mode">
            <Icon name={iconName} size="lg" tone="cyan" />
            <span>{label}</span>
          </div>
        );
      },
    },
    {
      field: 'compute_status',
      headerName: '数据状态',
      width: 110,
      valueGetter: (params) => getTagComputeStatusLabel(params.row),
      renderCell: (params) => <ComputeStatusChip row={params.row} />,
    },
    {
      field: 'last_computed_as_of',
      headerName: '最后计算至',
      width: 130,
      valueGetter: (params) => formatTagAsOfDate(params.row.last_computed_as_of),
    },
    {
      field: 'tag_definitions',
      headerName: '可产生的标签',
      minWidth: 160,
      flex: 0.55,
      sortable: false,
      valueGetter: (params) => (params.row.tag_definitions || [])
        .map((t) => t.display_name || t.name)
        .filter(Boolean)
        .join('、'),
      renderCell: (params) => {
        const defs = params.row.tag_definitions || [];
        if (!defs.length) {
          return <span className="ntq-muted">—</span>;
        }
        return (
          <div className="tag-list-cell-tags">
            {defs.map((t) => (
              <Tag key={t.name} variant="solid" color={tagColorFromName(t.name)}>
                {t.display_name || t.name}
              </Tag>
            ))}
          </div>
        );
      },
    },
  ]), [
    patchRunningRowProgress,
    pipelineBusy,
    pipelineLabel,
    refreshPipeline,
    running,
    runningTagId,
  ]);

  useEffect(() => {
    if (!running || !runningTagKey) return undefined;

    let cancelled = false;
    const pollSlot = pollRef.current;

    const pollOnce = () => {
      fetchTagRunProgress(runningTagKey, runningJobId)
        .then((p) => {
          if (cancelled) return;
          const pct = Number(p?.progress ?? 0);
          const status = String(p?.status || '');
          const label = String(p?.label || '').trim()
            || (status === 'completed' ? '完成' : '计算中…');
          patchRunningRowProgress(runningTagId, {
            pct: Number.isFinite(pct) ? pct : 0,
            label,
          });

          if (status === 'completed') {
            setRunningTagId('');
            setRunningTagKey('');
            setRunningJobId('');
            load();
            refreshPipeline();
            notifyTaskSuccess('tag');
            return;
          }
          if (status === 'failed') {
            showToast({
              status: 'error',
              content: String(p?.reason || p?.label || 'Tag 计算失败'),
            });
            setRunningTagId('');
            setRunningTagKey('');
            setRunningJobId('');
            setRows((prev) => clearRowProgress(prev));
            refreshPipeline();
            return;
          }

          pollSlot.timeoutId = window.setTimeout(pollOnce, 500);
        })
        .catch((err) => {
          if (cancelled) return;
          showToast({ status: 'error', content: err?.message || '轮询进度失败' });
          setRunningTagId('');
          setRunningTagKey('');
          setRunningJobId('');
          setRows((prev) => clearRowProgress(prev));
        });
    };

    pollOnce();
    return () => {
      cancelled = true;
      if (pollSlot.timeoutId) window.clearTimeout(pollSlot.timeoutId);
    };
  }, [load, patchRunningRowProgress, refreshPipeline, running, runningJobId, runningTagId, runningTagKey]);

  const statusTag = running
    ? { label: '计算中…', status: 'warning', variant: 'solid' }
    : pipelineBusy
      ? { label: '可排队', status: 'neutral', variant: 'outline' }
      : { label: '就绪', status: 'neutral', variant: 'outline' };

  return (
    <PageLayout
      className="tag-list-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="标签"
      bannerTitle="标签计算"
      bannerDescription="列出 userspace 中的 Tag scenario；对已启用场景点击「运行」触发计算。忙时可加入全局管道队列。"
      bannerRightSlot={(
        <Tag status={statusTag.status} variant={statusTag.variant}>
          {statusTag.label}
        </Tag>
      )}
      loading={!pageReady}
      loadingMessage="正在加载标签列表…"
    >
      <Section className="tag-list-page__stack" gap="md">
        {loadError ? <Message status="error">{loadError}</Message> : null}
        <DataEndTruncationAlert dataEnd={dataEnd} />
        {pipelineError ? (
          <Message status="warning" onClose={() => setPipelineError('')}>
            {pipelineError}
          </Message>
        ) : null}
        {pipelineBusy && pipelineLabel ? (
          <Message status="info">
            当前有其它任务占用数据管道（{pipelineLabel}）。仍可点运行，任务将加入队列。
          </Message>
        ) : null}

        <Section className="tag-list-grid" gap="md">
          <div className="tag-list-grid-toolbar">
            <SearchField
              fluid
              surface="glass"
              placeholder="搜索场景名或 Tag"
              label="搜索 Tag 场景"
              value={nameQuery}
              onChange={(e) => setNameQuery(e.target.value)}
            />
            <Button
              variant="glass"
              icon="refresh"
              onClick={load}
              disabled={loading || Boolean(runningTagId)}
            >
              刷新列表
            </Button>
          </div>

          <div className="tag-list-grid-body">
            <DataGrid
              autoHeight
              rows={displayRows}
              columns={columns}
              loading={loading}
              getRowHeight={() => 'auto'}
              slots={{ row: TagListGridRow }}
              pageSizeOptions={[10, 25, 50]}
              paginationModel={paginationModel}
              onPaginationModelChange={setPaginationModel}
              getRowId={(row) => row.id}
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
        </Section>
      </Section>

      <TagVisualization
        open={Boolean(vizTarget)}
        tagKey={vizTarget?.name || ''}
        displayName={vizTarget?.display_name || ''}
        onClose={() => setVizTarget(null)}
      />
    </PageLayout>
  );
}

export default TagListPage;
