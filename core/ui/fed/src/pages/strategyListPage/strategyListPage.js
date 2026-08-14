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
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  downloadStrategyPackage,
  fetchStrategyList,
  getStrategyDesignPath,
  getStrategyDisplayLabel,
  groupStrategiesByCategory,
} from '../../api/apis/strategyApi';
import PageLayout from '../../components/pageLayout/pageLayout';
import StrategyPackageImportDialog from '../../components/strategyPackageImportDialog/strategyPackageImportDialog';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../components/dataGridLoadingOverlay/dataGridLoadingOverlay';
import NtqIcon from '../../components/ntqIcon/ntqIcon';
import StrategyDescriptionText from '../../components/strategyDescriptionText/strategyDescriptionText';
import { buildStrategyDesignNavState } from '../strategyDesignPage/strategyDesignSessionState';
import './strategyListPage.scss';

/**
 * @param {object} props
 * @param {string} [props.listBasePath] 列表页路由（面包屑）
 * @param {(name: string) => string} [props.getEnterPath] 进入单策略调试页
 * @param {string} [props.navLabel] 主导航/面包屑标签
 * @param {string} [props.bannerTitle]
 * @param {string} [props.bannerDescription]
 */
const STRATEGY_LIST_BANNER_TITLE = '选择一个策略';
const STRATEGY_LIST_BANNER_DESCRIPTION =
  '请从表格中选择一个策略；支持按名称搜索。进入后可调参数、分步回测并对比版本。';

function StrategyListPage({
  listBasePath = '/strategy-design',
  getEnterPath = getStrategyDesignPath,
  navLabel = '制定策略',
  bannerTitle = STRATEGY_LIST_BANNER_TITLE,
  bannerDescription = STRATEGY_LIST_BANNER_DESCRIPTION,
}) {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [nameQuery, setNameQuery] = useState('');
  const [importOpen, setImportOpen] = useState(false);
  const [importNotice, setImportNotice] = useState(null);
  const [exportingName, setExportingName] = useState('');
  const [exportError, setExportError] = useState('');

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const id = String(r.name || '').toLowerCase();
      const path = String(r.path || '').toLowerCase();
      const key = String(r.key || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
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
  }, [rows, nameQuery]);

  const groupedRows = useMemo(
    () => groupStrategiesByCategory(displayRows),
    [displayRows],
  );

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

  const enterNavState = useCallback((row) => buildStrategyDesignNavState(row), []);

  const columns = [
    {
      field: 'display_name',
      headerName: '策略名',
      minWidth: 160,
      flex: 0.5,
      valueGetter: (params) => getStrategyDisplayLabel(params.row),
      renderCell: (params) => (
        <Link
          component={RouterLink}
          to={getEnterPath(params.row.name)}
          state={enterNavState(params.row)}
          underline="hover"
          onClick={(e) => e.stopPropagation()}
        >
          {params.value || params.row.name}
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
        const exportId = params.row.key || name;
        const isExporting = exportingName === exportId;
        return (
          <Stack direction="row" spacing={1} alignItems="center">
            <Link
              component={RouterLink}
              to={getEnterPath(name)}
              state={enterNavState(params.row)}
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
                handleExportStrategyPackage(exportId);
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
      sortable: false,
      renderCell: (params) => (
        <StrategyDescriptionText
          text={params.value}
          variant="body2"
          color="text.secondary"
          empty="—"
        />
      ),
    },
  ];

  const gridSx = {
    '& .MuiDataGrid-cell': {
      py: 1.25,
      alignItems: 'flex-start',
      whiteSpace: 'normal',
      lineHeight: 1.5,
    },
  };

  return (
    <PageLayout
      className="strategy-list-page"
      breadcrumbsItems={[{ label: navLabel, to: listBasePath }]}
      breadcrumbsCurrent="选择一个策略"
      bannerTitle={bannerTitle}
      bannerDescription={bannerDescription}
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

      <Paper className="strategy-list-grid">
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
          {groupedRows.length === 0 ? (
            <DataGrid
              autoHeight
              rows={[]}
              columns={columns}
              loading={loading}
              slots={NTQ_DATA_GRID_LOADING_SLOTS}
              localeText={zhCN}
              hideFooter
              disableRowSelectionOnClick
              sx={gridSx}
            />
          ) : (
            <Stack spacing={2.5}>
              {groupedRows.map(({ category, rows: categoryRows }) => (
                <Box key={category} className="strategy-list-category-section">
                  <Stack
                    direction="row"
                    alignItems="center"
                    spacing={1}
                    className="strategy-list-category-header"
                  >
                    <Typography variant="subtitle1" fontWeight={700}>
                      {category}
                    </Typography>
                    <Box
                      component="span"
                      className="strategy-list-category-count"
                      aria-label={`${categoryRows.length} 个策略`}
                    >
                      {categoryRows.length}
                    </Box>
                  </Stack>
                  <DataGrid
                    autoHeight
                    rows={categoryRows}
                    columns={columns}
                    loading={loading}
                    getRowHeight={() => 'auto'}
                    slots={NTQ_DATA_GRID_LOADING_SLOTS}
                    localeText={zhCN}
                    hideFooter
                    disableRowSelectionOnClick
                    sx={gridSx}
                    onRowDoubleClick={(params) => {
                      navigate(getEnterPath(params.row.name), {
                        state: enterNavState(params.row),
                      });
                    }}
                  />
                </Box>
              ))}
            </Stack>
          )}
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
