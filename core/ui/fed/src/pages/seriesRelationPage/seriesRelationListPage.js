import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  fetchSeriesRelationList,
  getSeriesRelationPath,
} from 'api/seriesRelationApi';
import PageLayout from 'views/pageLayout';
import SearchField from 'views/searchField';
import Button from 'views/ntqButton';
import Message from 'views/message';
import { NTQ_DATA_GRID_LOADING_SLOTS } from 'views/dataGridLoadingOverlay';
import { showToast } from 'containers/toast';
import './seriesRelationPage.scss';

function SeriesRelationListPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pageReady, setPageReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });

  const [newOpen, setNewOpen] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newDisplayName, setNewDisplayName] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchSeriesRelationList({ page: 1, limit: 500 })
      .then((res) => {
        setRows(
          (res.data || []).map((item) => ({
            ...item,
            id: item.key,
          })),
        );
      })
      .catch((err) => {
        setRows([]);
        setLoadError(err?.message || '加载序列关系列表失败');
      })
      .finally(() => {
        setLoading(false);
        setPageReady(true);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPaginationModel((m) => ({ ...m, page: 0 }));
  }, [nameQuery]);

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const key = String(r.key || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
      return key.includes(q) || label.includes(q);
    });
  }, [rows, nameQuery]);

  const enterScene = useCallback((key, state) => {
    if (!key) return;
    navigate(getSeriesRelationPath(key), { state: state || undefined });
  }, [navigate]);

  const confirmNew = () => {
    const key = String(newKey || '').trim();
    if (!key) {
      showToast({ severity: 'error', content: '请填写场景 key' });
      return;
    }
    setNewOpen(false);
    enterScene(key, {
      isNew: true,
      display_name: String(newDisplayName || '').trim() || key,
    });
  };

  const columns = useMemo(() => ([
    {
      field: 'display_name',
      headerName: '名称',
      minWidth: 200,
      flex: 0.5,
      renderCell: (params) => (
        <Typography
          component={RouterLink}
          to={getSeriesRelationPath(params.row.key)}
          variant="body2"
          fontWeight={700}
          className="ntq-srel-list-link"
        >
          {params.value || params.row.key}
        </Typography>
      ),
    },
    {
      field: 'key',
      headerName: 'Key',
      minWidth: 180,
      flex: 0.4,
      renderCell: (params) => (
        <Typography variant="body2" color="text.secondary" className="ntq-srel-list-key">
          {params.value}
        </Typography>
      ),
    },
    {
      field: 'has_results',
      headerName: '结果',
      width: 110,
      renderCell: (params) => (
        params.value ? (
          <Chip size="small" color="success" label="有结果" />
        ) : (
          <Chip size="small" variant="outlined" label="未跑批" />
        )
      ),
    },
    {
      field: 'actions',
      headerName: '',
      width: 120,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Button
          size="small"
          variant="glass"
          component={RouterLink}
          to={getSeriesRelationPath(params.row.key)}
        >
          进入
        </Button>
      ),
    },
  ]), []);

  return (
    <PageLayout
      className="ntq-srel-list-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="序列关系"
      bannerTitle="序列关系"
      bannerDescription="选择一条序列关系场景进行配置与跑批，或新建场景。"
      loading={!pageReady}
      loadingMessage="正在加载序列关系…"
    >
      {loadError ? (
        <Message severity="error" className="ntq-srel-list-alert">{loadError}</Message>
      ) : null}

      <Paper className="ntq-srel-list-grid">
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'stretch', sm: 'center' }}
          spacing={1.5}
          className="ntq-srel-list-toolbar"
        >
          <SearchField
            fluid
            placeholder="搜索名称或 Key"
            label="搜索序列关系"
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
          />
          <Button
            variant="glass"
            icon="refresh"
            onClick={load}
            disabled={loading}
          >
            刷新
          </Button>
          <Button
            variant="primary"
            icon="add"
            onClick={() => {
              setNewKey('');
              setNewDisplayName('');
              setNewOpen(true);
            }}
          >
            新建
          </Button>
        </Stack>

        <Box className="ntq-srel-list-grid-body">
          <DataGrid
            autoHeight
            rows={displayRows}
            columns={columns}
            loading={loading}
            disableRowSelectionOnClick
            pageSizeOptions={[10, 25, 50]}
            paginationModel={paginationModel}
            onPaginationModelChange={setPaginationModel}
            localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
            slots={NTQ_DATA_GRID_LOADING_SLOTS}
            getRowId={(row) => row.id}
            onRowDoubleClick={(params) => enterScene(params.row.key)}
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

      <Dialog open={newOpen} onClose={() => setNewOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>新建序列关系场景</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 1 }}>
            <TextField
              size="small"
              label="场景 key"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder="如 banks_vs_macro"
              fullWidth
              autoFocus
            />
            <TextField
              size="small"
              label="显示名（可选）"
              value={newDisplayName}
              onChange={(e) => setNewDisplayName(e.target.value)}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button variant="ghost" onClick={() => setNewOpen(false)}>取消</Button>
          <Button variant="primary" onClick={confirmNew}>创建</Button>
        </DialogActions>
      </Dialog>
    </PageLayout>
  );
}

export default SeriesRelationListPage;
