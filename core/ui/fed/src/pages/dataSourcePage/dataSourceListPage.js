import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
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
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  fetchDataSourceFreshness,
  fetchDataSourceList,
  getDataSourceAuthLabel,
  getDataSourceDisplayLabel,
  getDataSourceOriginLabel,
  getDataSourceRenewTypeIcon,
  getDataSourceRenewTypeLabel,
  getDataSourceUpdateStatusLabel,
} from '../../api/apis/dataSourceApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../components/dataGridLoadingOverlay/dataGridLoadingOverlay';
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import NtqRainbowRunButton from '../../components/ntqRainbowRunButton/ntqRainbowRunButton';
import './dataSourceListPage.scss';

function UpdateStatusChip({ row }) {
  const label = getDataSourceUpdateStatusLabel(row);
  const status = String(row.update_status || '').trim();
  if (row.freshness_pending) {
    return <Chip size="small" variant="outlined" label={label} />;
  }
  if (status === 'up_to_date') {
    return <Chip size="small" color="success" variant="outlined" label={label} />;
  }
  return <Chip size="small" color="warning" label={label} />;
}

function DataSourceListPage() {
  const [rows, setRows] = useState([]);
  const [dataEnd, setDataEnd] = useState({});
  const [loading, setLoading] = useState(true);
  const [freshnessLoading, setFreshnessLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [updateNotice, setUpdateNotice] = useState('');
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const key = String(r.name || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
      const providers = String(r.providers_label || '').toLowerCase();
      return key.includes(q) || label.includes(q) || providers.includes(q);
    });
  }, [rows, nameQuery]);

  const loadFreshness = useCallback((sourceNames) => {
    setFreshnessLoading(true);
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
        setRows((prev) => prev.map((row) => ({
          ...row,
          freshness_pending: false,
          update_status: 'needs_update',
          update_status_label: '—',
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
        loadFreshness(nextRows.map((row) => row.name));
      })
      .catch((e) => {
        setRows([]);
        setDataEnd({});
        setLoadError(e?.message || '加载数据源列表失败');
        setLoading(false);
      });
  }, [loadFreshness]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPaginationModel((m) => ({ ...m, page: 0 }));
  }, [nameQuery]);

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
        const canUpdate = Boolean(row.can_renew);
        let title = '更新执行接口开发中，下一版接入';
        if (!canUpdate && row.requires_auth && !row.auth_ready) {
          title = row.auth_hint || '未配置 Token，无法更新';
        } else if (!canUpdate) {
          title = '当前不可更新';
        }
        return (
          <Tooltip title={title}>
            <span className="data-source-list-update-btn-wrap">
              <NtqRainbowRunButton
                disabled={!canUpdate}
                ariaLabel="更新数据源"
                onClick={(e) => {
                  e.stopPropagation();
                  if (!canUpdate) return;
                  setUpdateNotice('更新执行接口开发中，下一版接入。');
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
      width: 110,
      valueGetter: (params) => getDataSourceUpdateStatusLabel(params.row),
      renderCell: (params) => <UpdateStatusChip row={params.row} />,
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
      width: 120,
      valueGetter: (params) => getDataSourceRenewTypeLabel(params.row),
      renderCell: (params) => {
        const mode = params.row.renew_type;
        const iconName = getDataSourceRenewTypeIcon(mode);
        return (
          <Stack direction="row" spacing={0.75} alignItems="center">
            <NtqIcon
              name={iconName}
              size={18}
              tone="muted"
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
  ]), []);

  return (
    <PageLayout
      className="data-source-list-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="数据源"
      bannerTitle="数据源"
      bannerDescription="查看已配置的数据源、Provider 认证与更新策略；Token 未配置时更新按钮不可用。"
    >
      {loadError ? <Alert severity="error" className="data-source-list-alert">{loadError}</Alert> : null}
      {dataEnd.is_end_date_truncated && dataEnd.truncation_hint ? (
        <Alert severity="warning" className="data-source-list-alert">
          {dataEnd.truncation_hint}
          {dataEnd.truncation_settings_path ? (
            <>
              {' '}
              <Typography
                component={RouterLink}
                to={dataEnd.truncation_settings_path}
                sx={{ color: 'inherit', fontWeight: 700, textDecoration: 'underline' }}
              >
                前往设置 → 数据范围
              </Typography>
              {' '}
              修改。
            </>
          ) : null}
        </Alert>
      ) : null}
      {updateNotice ? (
        <Alert
          severity="info"
          className="data-source-list-alert"
          onClose={() => setUpdateNotice('')}
        >
          {updateNotice}
        </Alert>
      ) : null}

      <Paper className="data-source-list-grid">
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'stretch', sm: 'center' }}
          spacing={1.5}
          className="data-source-list-grid-toolbar"
        >
          <TextField
            size="small"
            placeholder="搜索名称、Key 或 Provider"
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            inputProps={{ 'aria-label': '搜索数据源' }}
            className="data-source-list-search"
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
            disabled={loading || freshnessLoading}
            className="ntq-glass-outline-btn"
            startIcon={<NtqIcon name="refresh" size={22} tone="muted" />}
          >
            刷新列表
          </Button>
        </Stack>

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
            slots={NTQ_DATA_GRID_LOADING_SLOTS}
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
