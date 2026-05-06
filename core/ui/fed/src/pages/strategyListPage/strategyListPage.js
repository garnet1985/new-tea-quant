import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Chip,
  InputAdornment,
  Link,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import SearchIcon from '@mui/icons-material/Search';
import { fetchStrategyList, getStrategyWorkbenchPath } from '../../api/apis/strategyApi';
import './strategyListPage.scss';

function StrategyListPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 10 });

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => String(r.name).toLowerCase().includes(q));
  }, [rows, nameQuery]);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    fetchStrategyList()
      .then((res) => {
        setRows(res.data);
      })
      .catch((e) => {
        setLoadError(e?.message || '加载失败');
        setRows([]);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPaginationModel((m) => ({ ...m, page: 0 }));
  }, [nameQuery]);

  const columns = [
    {
      field: 'name',
      headerName: '策略名',
      minWidth: 160,
      flex: 0.5,
      renderCell: (params) => (
        <Link
          component={RouterLink}
          to={getStrategyWorkbenchPath(params.row.name)}
          underline="hover"
          onClick={(e) => e.stopPropagation()}
        >
          {params.value}
        </Link>
      ),
    },
    {
      field: 'is_enabled',
      headerName: '状态',
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
      width: 120,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Link
          component={RouterLink}
          to={getStrategyWorkbenchPath(params.row.name)}
          underline="hover"
          onClick={(e) => e.stopPropagation()}
        >
          进入调试
        </Link>
      ),
    },
    { field: 'description', headerName: '描述', minWidth: 240, flex: 1.5 },
  ];

  return (
    <Box className="strategy-list-page" sx={{ p: 2 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Breadcrumbs separator={<NavigateNextIcon fontSize="small" />}>
          <Link component={RouterLink} underline="hover" color="inherit" to="/strategy-workbench">
            策略工作台
          </Link>
          <Typography color="text.primary">策略列表</Typography>
        </Breadcrumbs>
        <Button variant="outlined" size="small" onClick={load} disabled={loading}>
          刷新
        </Button>
      </Stack>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        alignItems={{ xs: 'stretch', sm: 'center' }}
        justifyContent="space-between"
        spacing={1.5}
        sx={{ mb: 1 }}
      >
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          策略列表
        </Typography>
        <TextField
          size="small"
          placeholder="按策略名筛选，例如 example"
          value={nameQuery}
          onChange={(e) => setNameQuery(e.target.value)}
          inputProps={{ 'aria-label': '按策略名搜索' }}
          sx={{ minWidth: { xs: '100%', sm: 280 }, maxWidth: 400 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Stack>
      <Typography color="text.secondary" component="div" variant="body2" sx={{ mb: 2 }}>
        本页为进入系统后的落地页。列表数据来自 BFF{' '}
        <code>GET /api/v1/strategies/list</code>
        ，列字段对应各策略 <code>settings</code> 中 meta 段（
        <code>name</code>、<code>description</code>、<code>is_enabled</code>
        ），与各策略目录下 <code>settings.py</code> 一致。
      </Typography>
      {loadError ? <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert> : null}
      <Box sx={{ width: '100%', minHeight: 400 }}>
        <DataGrid
          autoHeight
          rows={displayRows}
          columns={columns}
          loading={loading}
          localeText={zhCN}
          disableRowSelectionOnClick
          onRowDoubleClick={(params) => {
            navigate(getStrategyWorkbenchPath(params.row.name));
          }}
          // 仅 [10]：MUI TablePagination 在仅一项时不渲染 “Rows per page” 与下拉（避免英文标签）
          pageSizeOptions={[10]}
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
        />
      </Box>
    </Box>
  );
}

export default StrategyListPage;
