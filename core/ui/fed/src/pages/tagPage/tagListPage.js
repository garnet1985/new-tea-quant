import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { DataGrid, GridRow } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
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
} from '../../api/apis/tagApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import DataEndTruncationAlert from '../../components/dataEndTruncationAlert/dataEndTruncationAlert';
import NtqHelpTooltip from '../../components/ntqHelpTooltip/ntqHelpTooltip';
import StrategyDescriptionText from '../../components/strategyDescriptionText/strategyDescriptionText';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../components/dataGridLoadingOverlay/dataGridLoadingOverlay';
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import NtqRainbowRunButton from '../../components/ntqRainbowRunButton/ntqRainbowRunButton';
import './tagListPage.scss';

function clearRowProgress(rows) {
  return rows.map((row) => {
    if (!row.__progress) return row;
    const next = { ...row };
    delete next.__progress;
    return next;
  });
}

function ComputeStatusChip({ row }) {
  const label = getTagComputeStatusLabel(row);
  const status = String(row.compute_status || '').trim();
  const hint = String(row.compute_status_hint || '').trim();
  let chip;
  if (status === 'up_to_date') {
    chip = <Chip size="small" color="success" variant="outlined" label={label} />;
  } else if (status === 'needs_recompute') {
    chip = <Chip size="small" color="warning" label={label} />;
  } else {
    chip = <Chip size="small" variant="outlined" label={label} />;
  }
  if (!hint || status === 'up_to_date') {
    return chip;
  }
  return (
    <Tooltip title={hint}>
      <span>{chip}</span>
    </Tooltip>
  );
}

function TagListPage() {
  const [rows, setRows] = useState([]);
  const [dataEnd, setDataEnd] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 10 });

  const [pipelineBusy, setPipelineBusy] = useState(false);
  const [pipelineLabel, setPipelineLabel] = useState('');

  const [runningTagId, setRunningTagId] = useState('');
  const [runningTagKey, setRunningTagKey] = useState('');
  const [runningJobId, setRunningJobId] = useState('');
  const [runError, setRunError] = useState('');

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
      })
      .catch(() => {
        setPipelineBusy(false);
        setPipelineLabel('');
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
      .finally(() => setLoading(false));
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
          <Stack direction="row" spacing={0.5} alignItems="center" sx={{ minWidth: 0 }}>
            <Typography variant="body2" fontWeight={700} noWrap>
              {label}
            </Typography>
            {description ? (
              <NtqHelpTooltip
                title={(
                  <StrategyDescriptionText
                    text={description}
                    variant="body2"
                    color="inherit"
                    empty=""
                  />
                )}
                ariaLabel={`${label} 简介`}
              />
            ) : null}
          </Stack>
        );
      },
    },
    {
      field: 'is_enabled',
      headerName: '启用状态',
      width: 110,
      renderCell: (params) => (params.value ? (
        <Chip size="small" color="success" label="已启用" />
      ) : (
        <Chip size="small" color="default" label="已禁用" />
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
        const blocked = pipelineBusy && !isThisRunning;
        const disableRun = !enabled || Boolean(runningTagId) || blocked;
        let title = '';
        if (!enabled) title = 'Scenario 未启用';
        else if (blocked) title = pipelineLabel ? `系统忙：${pipelineLabel}` : '系统有其他任务进行中';
        else if (running && !isThisRunning) title = '已有 Tag 任务在运行';
        else if (!title) title = '运行 Tag 计算';

        return (
          <Tooltip title={title}>
            <span className="tag-list-run-btn-wrap">
              <NtqRainbowRunButton
                disabled={disableRun}
                ariaLabel="运行 Tag 计算"
                onClick={(e) => {
                  e.stopPropagation();
                  setRunError('');
                  setRunningTagId(id);
                  setRunningTagKey(params.row.name);
                  setRunningJobId('');
                  patchRunningRowProgress(id, { pct: 0, label: '准备中…' });
                  startTagRun(params.row.name)
                    .then((res) => {
                      const jobId = String(res?.job_id || '').trim();
                      if (!jobId) throw new Error('启动失败：未返回 job_id');
                      setRunningTagId(id);
                      setRunningJobId(jobId);
                    })
                    .catch((err) => {
                      setRunError(err?.message || '启动 Tag 计算失败');
                      setRunningTagId('');
                      setRunningTagKey('');
                      setRunningJobId('');
                      setRows((prev) => clearRowProgress(prev));
                      refreshPipeline();
                    });
                }}
              />
            </span>
          </Tooltip>
        );
      },
    },
    {
      field: 'update_mode',
      headerName: '更新方式',
      width: 110,
      renderCell: (params) => {
        const mode = params.row.update_mode;
        const label = getTagUpdateModeLabel(mode);
        const iconName = getTagUpdateModeIcon(mode);
        return (
          <Stack direction="row" spacing={0.75} alignItems="center">
            <NtqIcon
              name={iconName}
              size={18}
              tone="muted"
            />
            <Typography variant="body2">{label}</Typography>
          </Stack>
        );
      },
    },
    {
      field: 'compute_status',
      headerName: '计算状态',
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
          return <Typography variant="body2" color="text.secondary">—</Typography>;
        }
        return (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
            {defs.map((t) => (
              <Chip
                key={t.name}
                size="small"
                variant="outlined"
                label={t.display_name || t.name}
              />
            ))}
          </Stack>
        );
      },
    },
  ]), [patchRunningRowProgress, pipelineBusy, pipelineLabel, running, runningTagId, refreshPipeline]);

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
            return;
          }
          if (status === 'failed') {
            setRunError(String(p?.reason || p?.label || 'Tag 计算失败'));
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
          setRunError(err?.message || '轮询进度失败');
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

  const statusChip = running
    ? { label: '计算中…', color: 'warning', variant: 'filled' }
    : pipelineBusy
      ? { label: '系统忙', color: 'default', variant: 'outlined' }
      : { label: '就绪', color: 'default', variant: 'outlined' };

  return (
    <PageLayout
      className="tag-list-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="标签"
      bannerTitle="标签计算"
      bannerDescription="列出 userspace 中的 Tag scenario；对已启用场景点击「运行」触发计算。同一时刻仅可运行一个 Tag 任务。"
      bannerRightSlot={(
        <Chip
          size="small"
          label={statusChip.label}
          color={statusChip.color}
          variant={statusChip.variant}
        />
      )}
    >
      {loadError ? <Alert severity="error" className="tag-list-alert">{loadError}</Alert> : null}
      <DataEndTruncationAlert dataEnd={dataEnd} className="tag-list-alert" />
      {runError ? (
        <Alert severity="error" className="tag-list-alert" onClose={() => setRunError('')}>
          {runError}
        </Alert>
      ) : null}
      {pipelineBusy && pipelineLabel ? (
        <Alert severity="info" className="tag-list-alert">
          当前有其它任务占用数据管道（{pipelineLabel}），Tag 运行已暂时禁用。
        </Alert>
      ) : null}

      <Paper className="tag-list-grid">
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'stretch', sm: 'center' }}
          spacing={1.5}
          className="tag-list-grid-toolbar"
        >
          <TextField
            size="small"
            placeholder="搜索场景名或 Tag"
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            inputProps={{ 'aria-label': '搜索 Tag 场景' }}
            className="tag-list-search"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <NtqIcon name="search" size={22} tone="muted" />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="outlined"
            size="small"
            onClick={load}
            disabled={loading || Boolean(runningTagId)}
            className="ntq-glass-outline-btn"
            startIcon={<NtqIcon name="refresh" size={22} tone="muted" />}
          >
            刷新列表
          </Button>
        </Stack>

        <Box className="tag-list-grid-body">
          <DataGrid
            autoHeight
            rows={displayRows}
            columns={columns}
            loading={loading}
            getRowHeight={() => 'auto'}
            slots={{
              ...NTQ_DATA_GRID_LOADING_SLOTS,
              row: TagListGridRow,
            }}
            disableRowSelectionOnClick
            pageSizeOptions={[10, 25, 50]}
            paginationModel={paginationModel}
            onPaginationModelChange={setPaginationModel}
            localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
            getRowId={(row) => row.id}
            sx={{
              border: 'none',
              '& .MuiDataGrid-cell': {
                py: 1.25,
                alignItems: 'flex-start',
                whiteSpace: 'normal',
                lineHeight: 1.5,
              },
            }}
          />
        </Box>
      </Paper>
    </PageLayout>
  );
}

export default TagListPage;
