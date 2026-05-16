import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Chip,
  InputAdornment,
  Link,
  Paper,
  Stack,
  Button,
  TextField,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import SearchIcon from '@mui/icons-material/Search';
import { fetchStrategyList, getStrategyWorkbenchPath } from '../../api/apis/strategyApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import { ReactComponent as RefreshIcon } from '../../assets/icon/refresh.svg';
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
    <PageLayout
      className="strategy-list-page"
      breadcrumbsItems={[{ label: '策略实验室', to: '/strategy-workbench' }]}
      breadcrumbsCurrent="选择一个策略"
      bannerTitle="选择一个策略"
      bannerDescription="请从表格中选择一个策略进入策略实验室；支持按名称搜索。进入后可调参数、分步回测并对比版本。"
    >
      {loadError ? <Alert severity="error" className="strategy-list-alert">{loadError}</Alert> : null}

      <Paper className="strategy-list-grid ntq-glass-blur">
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'stretch', sm: 'center' }}
          spacing={1.5}
          className="strategy-list-grid-toolbar"
        >
          <TextField
            size="small"
            placeholder="输入策略名称搜索"
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            inputProps={{ 'aria-label': '按策略名搜索' }}
            className="strategy-list-search"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="outlined"
            size="small"
            onClick={load}
            disabled={loading}
            className="strategy-list-refresh-btn"
            startIcon={<RefreshIcon className="strategy-list-refresh-icon" />}
          >
            刷新策略
          </Button>
        </Stack>

        <Box className="strategy-list-grid-body">
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
      </Paper>
    </PageLayout>
  );
}

export default StrategyListPage;
