import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  fetchDataContractList,
  getDataContractDisplayLabel,
  getDataContractOriginLabel,
} from '../../api/apis/dataContractApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../components/dataGridLoadingOverlay/dataGridLoadingOverlay';
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import './dataContractListPage.scss';

function BoolChip({ value, trueLabel, falseLabel }) {
  return value ? (
    <Chip size="small" color="success" label={trueLabel} />
  ) : (
    <Chip size="small" variant="outlined" label={falseLabel} />
  );
}

function DataContractListPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const key = String(r.key || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
      return key.includes(q) || label.includes(q);
    });
  }, [rows, nameQuery]);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchDataContractList({ page: 1, limit: 500 })
      .then((res) => {
        setRows(Array.isArray(res?.data) ? res.data : []);
      })
      .catch((e) => {
        setRows([]);
        setLoadError(e?.message || '加载数据契约列表失败');
      })
      .finally(() => setLoading(false));
  }, []);

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
      minWidth: 180,
      flex: 0.45,
      valueGetter: (params) => getDataContractDisplayLabel(params.row),
      renderCell: (params) => (
        <Typography variant="body2" fontWeight={700}>
          {params.value || params.row.key}
        </Typography>
      ),
    },
    {
      field: 'key',
      headerName: 'Key',
      minWidth: 220,
      flex: 0.55,
      renderCell: (params) => (
        <Typography variant="body2" color="text.secondary" className="data-contract-list-key">
          {params.value}
        </Typography>
      ),
    },
    {
      field: 'origin',
      headerName: '来源',
      width: 100,
      valueGetter: (params) => getDataContractOriginLabel(params.row.origin),
      renderCell: (params) => (
        params.row.is_custom ? (
          <Chip size="small" color="secondary" variant="outlined" label={params.value} />
        ) : (
          <Chip size="small" variant="outlined" label={params.value} />
        )
      ),
    },
    {
      field: 'is_time_series',
      headerName: '时序',
      width: 100,
      renderCell: (params) => (
        <BoolChip value={Boolean(params.value)} trueLabel="是" falseLabel="否" />
      ),
    },
    {
      field: 'is_per_entity',
      headerName: '按实体',
      width: 100,
      renderCell: (params) => (
        <BoolChip value={Boolean(params.value)} trueLabel="是" falseLabel="否" />
      ),
    },
  ]), []);

  return (
    <PageLayout
      className="data-contract-list-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="数据契约"
      bannerTitle="数据契约"
      bannerDescription="列出 core 与 userspace 合并后的 DataKey 目录，便于在策略与 Tag 配置中查找 data key。"
    >
      {loadError ? <Alert severity="error" className="data-contract-list-alert">{loadError}</Alert> : null}

      <Paper className="data-contract-list-grid">
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'stretch', sm: 'center' }}
          spacing={1.5}
          className="data-contract-list-grid-toolbar"
        >
          <TextField
            size="small"
            placeholder="搜索名称或 Key"
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            inputProps={{ 'aria-label': '搜索数据契约' }}
            className="data-contract-list-search"
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
            disabled={loading}
            className="ntq-glass-outline-btn"
            startIcon={<NtqIcon name="refresh" size={22} tone="muted" />}
          >
            刷新列表
          </Button>
        </Stack>

        <Box className="data-contract-list-grid-body">
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

export default DataContractListPage;
