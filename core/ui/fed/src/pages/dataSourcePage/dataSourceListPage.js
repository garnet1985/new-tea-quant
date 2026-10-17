import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Chip,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import { DataGrid, GridRow } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  fetchDataSourceFreshness,
  fetchDataSourceList,
  fetchDataSourceRenewStatus,
  startDataSourceRenew,
  getDataSourceAuthLabel,
  getDataSourceDisplayLabel,
  getDataSourceOriginLabel,
  getDataSourceRenewTypeIcon,
  getDataSourceRenewTypeLabel,
  getDataSourceUpdateStatusLabel,
} from '../../api/dataSourceApi';
import PageLayout from '../../views/pageLayout';
import SearchField from '../../views/searchField';
import NtqButton from '../../views/ntqButton';
import DataEndTruncationAlert from '../../views/dataEndTruncationAlert';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../views/dataGridLoadingOverlay';
import NtqIcon from '../../views/ntqIcon';
import RainbowButton from '../../views/rainbowButton';
import FreshnessStatusChip from '../../views/freshnessStatusChip';
import Message from '../../views/message';
import { showToast } from 'containers/toast';
import { progressRatio } from 'service/progress/ratio';
import './dataSourceListPage.scss';

function RenewAccessTip() {
  return (
    <Box className="data-source-renew-tip">
      <span>未注册：拥有3年300只股票的演示数据（2023-2025年底）。</span>
      <span>注册后：拥有3年全市场的5000+股票数据（2023-2025年底）。</span>
      <span>注册并有1000点数：全市场所有股票从2008年开始的所有数据（每日更新）。</span>
    </Box>
  );
}

function formatElapsed(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  if (total < 60) return `${total}秒`;
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  if (minutes < 60) return rest ? `${minutes}分${rest}秒` : `${minutes}分`;
  const hours = Math.floor(minutes / 60);
  const min = minutes % 60;
  return min ? `${hours}小时${min}分` : `${hours}小时`;
}

function taskPercent(run, progress) {
  if (!run || run.status !== 'running' || !progress) return 0;
  if (progress.source && progress.source !== run.source) return 0;
  const total = Number(progress.subTotal);
  const done = Number(progress.sub);
  if (!Number.isFinite(total) || total <= 0) return 0;
  return Math.max(0, Math.min(100, (done / total) * 100));
}

function elapsedLabel(run, nowSec) {
  if (!run) return '—';
  if (run.status === 'running' && run.startedAt > 0) {
    return formatElapsed(Math.max(0, nowSec - run.startedAt));
  }
  if (run.status === 'pending') return '等待';
  if (run.totalSeconds != null && Number.isFinite(run.totalSeconds)) {
    return formatElapsed(run.totalSeconds);
  }
  return '—';
}

function settleTasks(status) {
  const tasks = Array.isArray(status?.tasks) ? status.tasks : [];
  if (status?.running) return tasks;
  return tasks.map((task) => {
    if (task.status === 'pending') return { ...task, status: 'idle' };
    if (task.status === 'running') {
      return { ...task, status: task.totalSeconds != null ? 'done' : 'idle' };
    }
    return task;
  });
}

function UpdateStatusChip({ row }) {
  return (
    <FreshnessStatusChip
      status={row.update_status}
      label={getDataSourceUpdateStatusLabel(row)}
      hint={row.update_status_hint}
      pending={Boolean(row.freshness_pending)}
    />
  );
}

function DataSourceListPage() {
  const [rows, setRows] = useState([]);
  const [dataEnd, setDataEnd] = useState({});
  const [loading, setLoading] = useState(true);
  const [pageReady, setPageReady] = useState(false);
  const [freshnessLoading, setFreshnessLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [freshnessError, setFreshnessError] = useState('');
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });
  const [renewing, setRenewing] = useState(false);
  const [renewSource, setRenewSource] = useState('');
  const [renewTasks, setRenewTasks] = useState([]);
  const [jobProgress, setJobProgress] = useState({
    source: '', step: 0, stepTotal: 0, sub: 0, subTotal: 0,
  });
  const [nowSec, setNowSec] = useState(() => Math.floor(Date.now() / 1000));
  const expectJobRef = useRef('');
  const watchRef = useRef(() => {});

  const taskByName = useMemo(() => {
    const map = {};
    renewTasks.forEach((task) => {
      if (task?.source) map[task.source] = task;
    });
    return map;
  }, [renewTasks]);

  const displayRows = useMemo(() => {
    const withRun = rows.map((row) => ({
      ...row,
      __run: taskByName[row.name],
    }));
    const q = nameQuery.trim().toLowerCase();
    if (!q) return withRun;
    return withRun.filter((r) => {
      const key = String(r.name || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
      const providers = String(r.providers_label || '').toLowerCase();
      return key.includes(q) || label.includes(q) || providers.includes(q);
    });
  }, [rows, nameQuery, taskByName]);

  const DataSourceGridRow = useCallback((rowProps) => {
    const run = rowProps.row.__run;
    const isRunning = run?.status === 'running';
    const pct = taskPercent(run);
    const extra = [
      isRunning ? 'data-source-list-row--running' : '',
      isRunning && pct <= 0 ? 'data-source-list-row--running-indeterminate' : '',
    ].filter(Boolean).join(' ');
    return (
      <GridRow
        {...rowProps}
        className={[rowProps.className, extra].filter(Boolean).join(' ')}
        style={{
          ...rowProps.style,
          ...(isRunning ? { '--data-source-run-pct': `${pct}%` } : undefined),
        }}
      />
    );
  }, []);

  const loadFreshness = useCallback((sourceNames) => {
    setFreshnessLoading(true);
    setFreshnessError('');
    fetchDataSourceFreshness(
      Array.isArray(sourceNames) && sourceNames.length > 0 ? { names: sourceNames } : {},
    )
      .then((res) => {
        const freshnessMap = res?.items && typeof res.items === 'object' ? res.items : {};
        setRows((prev) => prev.map((row) => {
          const patch = freshnessMap[row.name];
          if (!patch) return row;
          return { ...row, ...patch };
        }));
        if (res?.dataEnd && typeof res.dataEnd === 'object') {
          setDataEnd(res.dataEnd);
        }
      })
      .catch(() => {
        setFreshnessError('无法读取数据新鲜度，状态显示可能不准确。');
        setRows((prev) => prev.map((row) => ({
          ...row,
          freshness_pending: false,
        })));
      })
      .finally(() => setFreshnessLoading(false));
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchDataSourceList({ page: 1, limit: 500 })
      .then((res) => {
        const nextRows = Array.isArray(res?.data) ? res.data : [];
        setRows(nextRows);
        setDataEnd(res?.dataEnd && typeof res.dataEnd === 'object' ? res.dataEnd : {});
        setLoading(false);
        setPageReady(true);
        loadFreshness(nextRows.map((row) => row.name));
      })
      .catch((e) => {
        setRows([]);
        setDataEnd({});
        setLoadError(e?.message || '加载数据源列表失败');
        setLoading(false);
        setPageReady(true);
      });
  }, [loadFreshness]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPaginationModel((m) => ({ ...m, page: 0 }));
  }, [nameQuery]);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    let sawRunning = false;
    let inFlight = false;
    const schedule = (ms) => {
      window.clearTimeout(timer);
      timer = window.setTimeout(watch, ms);
    };
    const finish = (status) => {
      sawRunning = false;
      expectJobRef.current = '';
      setRenewing(false);
      setRenewSource('');
      if (status.error) {
        showToast({ severity: 'error', content: status.error });
        return;
      }
      showToast({
        severity: status.message ? 'info' : 'success',
        content: status.message || '数据更新已结束',
      });
      loadFreshness();
    };
    const watch = () => {
      if (cancelled || inFlight) return;
      inFlight = true;
      fetchDataSourceRenewStatus()
        .then((status) => {
          if (cancelled) return;
          setRenewTasks(settleTasks(status));
          setJobProgress(status.progress || {
            source: '', step: 0, stepTotal: 0, sub: 0, subTotal: 0,
          });
          if (status.running) {
            sawRunning = true;
            setRenewing(true);
            const current = (status.tasks || []).find((task) => task.status === 'running');
            setRenewSource(status.source || current?.source || '');
            schedule(1000);
            return;
          }
          const expected = expectJobRef.current;
          const finishedThisClick = Boolean(expected) && status.job_id === expected;
          if (sawRunning || finishedThisClick) {
            finish(status);
          }
          schedule(1500);
        })
        .catch((err) => {
          if (cancelled || err?.status === 404) return;
          schedule(4000);
        })
        .finally(() => {
          inFlight = false;
        });
    };
    watchRef.current = () => {
      window.clearTimeout(timer);
      watch();
    };
    watch();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      watchRef.current = () => {};
    };
  }, [loadFreshness]);

  useEffect(() => {
    if (!renewing) return undefined;
    const id = window.setInterval(() => {
      setNowSec(Math.floor(Date.now() / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [renewing]);

  const runningTask = renewTasks.find((task) => task.status === 'running') || null;
  const runningTitle = useMemo(() => {
    const key = runningTask?.source || renewSource;
    if (!key) return renewing ? '需要更新的数据源' : '';
    const row = rows.find((item) => item.name === key);
    return getDataSourceDisplayLabel(row) || key;
  }, [renewSource, renewing, rows, runningTask]);

  useEffect(() => {
    const key = runningTask?.source;
    if (!key) return;
    const index = displayRows.findIndex((row) => row.name === key);
    if (index < 0) return;
    const page = Math.floor(index / paginationModel.pageSize);
    setPaginationModel((model) => (model.page === page ? model : { ...model, page }));
  }, [displayRows, paginationModel.pageSize, runningTask]);

  const beginRenew = useCallback((source = '') => {
    const key = String(source || '').trim();
    startDataSourceRenew(key)
      .then((started) => {
        expectJobRef.current = started.job_id || '';
        setRenewing(true);
        setRenewSource(key);
        watchRef.current();
        showToast({
          severity: 'info',
          content: key ? '已开始更新这一项' : '已开始更新需要更新的数据源',
        });
      })
      .catch((err) => {
        showToast({ severity: 'error', content: err?.message || '无法开始更新' });
      });
  }, []);

  const columns = useMemo(() => ([
    {
      field: 'display_name',
      headerName: '名称',
      minWidth: 160,
      flex: 0.4,
      valueGetter: (params) => getDataSourceDisplayLabel(params.row),
      renderCell: (params) => (
        <Typography variant="body2" fontWeight={700}>
          {params.value || params.row.name}
        </Typography>
      ),
    },
    {
      field: 'providers_label',
      headerName: '数据来源',
      minWidth: 120,
      flex: 0.25,
      renderCell: (params) => (
        <Typography variant="body2" color="text.secondary">
          {params.value || '—'}
        </Typography>
      ),
    },
    {
      field: 'update_action',
      headerName: '更新',
      width: 72,
      sortable: false,
      renderCell: (params) => {
        const row = params.row;
        const canUpdate = Boolean(row.can_renew) && !renewing;
        const runningThis = row.__run?.status === 'running';
        let title = '只更新这一项';
        if (runningThis) {
          title = '正在更新这一项';
        } else if (renewing) {
          title = renewSource ? '正在更新另一项' : '排队中';
        } else if (!row.can_renew && row.requires_auth && !row.auth_ready) {
          title = row.auth_hint || '未配置 Token，无法更新';
        } else if (!row.can_renew) {
          title = '当前不可更新';
        }
        return (
          <Tooltip title={title}>
            <span className="data-source-list-update-btn-wrap">
              <RainbowButton
                icon="play"
                disabled={!canUpdate}
                aria-label={`更新${getDataSourceDisplayLabel(row)}`}
                onClick={(e) => {
                  e.stopPropagation();
                  if (!canUpdate) return;
                  beginRenew(row.name);
                }}
              />
            </span>
          </Tooltip>
        );
      },
    },
    {
      field: 'update_status',
      headerName: '数据状态',
      width: 220,
      valueGetter: (params) => getDataSourceUpdateStatusLabel(params.row),
      renderCell: (params) => {
        const run = params.row.__run;
        if (run?.status === 'running') {
          const pct = taskPercent(run, jobProgress);
          const text = jobProgress.subTotal > 0 && jobProgress.source === run.source
            ? `${jobProgress.sub}/${jobProgress.subTotal}`
            : '正在获取';
          const head = pct > 0 ? `${Math.round(pct)}%` : '';
          return (
            <Tooltip title={text}>
              <Typography variant="body2" noWrap className="data-source-list-progress-label">
                {head ? `${head} ${text}` : text}
              </Typography>
            </Tooltip>
          );
        }
        if (run?.status === 'failed') {
          return (
            <Tooltip title={run.error || '更新失败'}>
              <Chip size="small" color="error" label="更新失败" />
            </Tooltip>
          );
        }
        return <UpdateStatusChip row={params.row} />;
      },
    },
    {
      field: 'elapsed',
      headerName: '总耗时',
      width: 110,
      sortable: false,
      valueGetter: (params) => elapsedLabel(params.row.__run, nowSec),
      renderCell: (params) => (
        <Typography variant="body2" className="data-source-list-elapsed">
          {params.value}
        </Typography>
      ),
    },
    {
      field: 'origin',
      headerName: '来源',
      width: 100,
      valueGetter: (params) => getDataSourceOriginLabel(params.row.origin),
      renderCell: (params) => (
        params.row.is_custom ? (
          <Chip size="small" color="secondary" variant="outlined" label={params.value} />
        ) : (
          <Chip size="small" variant="outlined" label={params.value} />
        )
      ),
    },
    {
      field: 'renew_type',
      headerName: '更新方式',
      width: 148,
      valueGetter: (params) => getDataSourceRenewTypeLabel(params.row),
      renderCell: (params) => {
        const mode = params.row.renew_type;
        const iconName = getDataSourceRenewTypeIcon(mode);
        return (
          <Stack direction="row" spacing={0.75} alignItems="center">
            <NtqIcon
              name={iconName}
              size={28}
              tone="cyan"
            />
            <Typography variant="body2">{params.value}</Typography>
          </Stack>
        );
      },
    },
    {
      field: 'renew_interval_days',
      headerName: '更新间隔',
      width: 110,
      valueGetter: (params) => {
        const days = params.row.renew_interval_days;
        if (days == null || days === '') return '—';
        return `${days} 天`;
      },
    },
    {
      field: 'rate_limit_per_minute',
      headerName: '限速',
      width: 100,
      valueGetter: (params) => {
        const limit = params.row.rate_limit_per_minute;
        if (limit == null || limit === '') return '—';
        return `${limit}/分钟`;
      },
    },
    {
      field: 'auth_ready',
      headerName: '认证',
      width: 110,
      valueGetter: (params) => getDataSourceAuthLabel(params.row),
      renderCell: (params) => {
        const row = params.row;
        if (!row.requires_auth) {
          return <Chip size="small" variant="outlined" label={params.value} />;
        }
        return row.auth_ready ? (
          <Chip size="small" color="success" label={params.value} />
        ) : (
          <Tooltip title={row.auth_hint || '未配置 Token'}>
            <Chip size="small" color="warning" variant="outlined" label={params.value} />
          </Tooltip>
        );
      },
    },
  ]), [beginRenew, jobProgress, nowSec, renewing, renewSource]);

  return (
    <PageLayout
      className="data-source-list-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="数据源"
      bannerTitle="数据源"
      bannerDescription="一键更新按顺序更新所有需要更新的数据源。正在更新的那一行会显示进度。每一行的按钮只更新那一项。"
      loading={!pageReady}
      loadingMessage="正在加载数据源…"
    >
      {loadError ? <Message severity="error" className="data-source-list-alert">{loadError}</Message> : null}
      {freshnessError ? (
        <Message
          severity="warning"
          className="data-source-list-alert"
          onClose={() => setFreshnessError('')}
        >
          {freshnessError}
        </Message>
      ) : null}
      <DataEndTruncationAlert dataEnd={dataEnd} className="data-source-list-alert" />

      <Paper className="data-source-list-grid">
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'stretch', sm: 'center' }}
          spacing={1.5}
          className="data-source-list-grid-toolbar"
        >
          <SearchField
            fluid
            placeholder="搜索名称、Key 或 Provider"
            label="搜索数据源"
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
          />
          <Tooltip title={<RenewAccessTip />}>
            <span>
              <NtqButton
                variant="primary"
                icon="play"
                onClick={() => beginRenew('')}
                disabled={loading || renewing || rows.every((row) => !row.can_renew)}
              >
                {renewing && !renewSource ? '更新中…' : '一键更新'}
              </NtqButton>
            </span>
          </Tooltip>
          <NtqButton
            variant="glass"
            icon="refresh"
            onClick={load}
            disabled={loading || freshnessLoading}
          >
            刷新列表
          </NtqButton>
        </Stack>
        {renewing ? (
          <Typography variant="body2" className="data-source-list-live">
            {`正在更新 ${jobProgress.source || runningTitle || '…'}`}
            {jobProgress.stepTotal > 0
              ? ` · ${jobProgress.step}/${jobProgress.stepTotal}`
              : ' · 正在获取'}
            {jobProgress.subTotal > 0 ? ` · ${jobProgress.sub}/${jobProgress.subTotal}` : ''}
            {jobProgress.stepTotal > 0
              ? ` · ${Math.round(progressRatio(jobProgress.step, jobProgress.stepTotal, jobProgress.sub, jobProgress.subTotal) * 100)}%`
              : ''}
            {runningTask?.startedAt ? ` · ${elapsedLabel(runningTask, nowSec)}` : ''}
          </Typography>
        ) : null}

        <Box className="data-source-list-grid-body">
          <DataGrid
            autoHeight
            rows={displayRows}
            columns={columns}
            loading={loading}
            disableRowSelectionOnClick
            pageSizeOptions={[10, 25, 50, 100]}
            paginationModel={paginationModel}
            onPaginationModelChange={setPaginationModel}
            localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
            slots={{
              ...NTQ_DATA_GRID_LOADING_SLOTS,
              row: DataSourceGridRow,
            }}
            getRowId={(row) => row.id}
            sx={{
              border: 'none',
              '& .MuiDataGrid-cell': {
                py: 1,
                alignItems: 'center',
              },
            }}
          />
        </Box>
      </Paper>
    </PageLayout>
  );
}

export default DataSourceListPage;
