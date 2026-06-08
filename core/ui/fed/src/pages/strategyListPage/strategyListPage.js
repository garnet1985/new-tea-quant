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
import {
  downloadStrategyPackage,
  fetchStrategyList,
  getStrategyWorkbenchPath,
} from '../../api/apis/strategyApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import StrategyPackageImportDialog from '../../components/strategyPackageImportDialog/strategyPackageImportDialog';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../components/dataGridLoadingOverlay/dataGridLoadingOverlay';
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import './strategyListPage.scss';

function StrategyListPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 10 });
  const [importOpen, setImportOpen] = useState(false);
  const [importNotice, setImportNotice] = useState(null);
  const [exportingName, setExportingName] = useState('');
  const [exportError, setExportError] = useState('');

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

  const handleExportStrategyPackage = useCallback(async (strategyName) => {
    if (!strategyName || exportingName) return;
    setExportingName(strategyName);
    setExportError('');
    try {
      await downloadStrategyPackage(strategyName, { scope: 'bundle' });
    } catch (e) {
      setExportError(e?.message || '导出失败');
    } finally {
      setExportingName('');
    }
  }, [exportingName]);

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
      width: 180,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const name = params.row.name;
        const isExporting = exportingName === name;
        return (
          <Stack direction="row" spacing={1} alignItems="center">
            <Link
              component={RouterLink}
              to={getStrategyWorkbenchPath(name)}
              underline="hover"
              onClick={(e) => e.stopPropagation()}
            >
              进入调试
            </Link>
            <Box component="span" sx={{ color: 'text.disabled', userSelect: 'none' }} aria-hidden>
              |
            </Box>
            <Link
              component="button"
              type="button"
              color="primary"
              underline="hover"
              disabled={Boolean(exportingName)}
              onClick={(e) => {
                e.stopPropagation();
                handleExportStrategyPackage(name);
              }}
              sx={{
                border: 'none',
                background: 'none',
                padding: 0,
                font: 'inherit',
                cursor: exportingName ? 'default' : 'pointer',
                opacity: exportingName && !isExporting ? 0.5 : 1,
              }}
            >
              {isExporting ? '导出中…' : '导出'}
            </Link>
          </Stack>
        );
      },
    },
    {
      field: 'description',
      headerName: '描述',
      minWidth: 240,
      flex: 1.5,
      valueFormatter: (params) => params.value || '—',
    },
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
      {importNotice ? (
        <Alert
          severity="success"
          className="strategy-list-alert"
          onClose={() => setImportNotice(null)}
        >
          {importNotice}
        </Alert>
      ) : null}
      {exportError ? (
        <Alert
          severity="error"
          className="strategy-list-alert"
          onClose={() => setExportError('')}
        >
          {exportError}
        </Alert>
      ) : null}

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
            刷新策略
          </Button>
          <Button
            variant="contained"
            color="primary"
            size="small"
            onClick={() => setImportOpen(true)}
            disabled={loading}
            className="ntq-cyan-fill-btn"
            startIcon={<NtqIcon name="uploadFile" size={22} />}
          >
            导入策略包
          </Button>
        </Stack>

        <Box className="strategy-list-grid-body">
          <DataGrid
            autoHeight
            rows={displayRows}
            columns={columns}
            loading={loading}
            slots={NTQ_DATA_GRID_LOADING_SLOTS}
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

      <StrategyPackageImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={(result) => {
          const name = result?.strategy_name || '策略包';
          setImportNotice(`已导入 ${name}，列表已刷新`);
          load();
        }}
      />
    </PageLayout>
  );
}

export default StrategyListPage;
