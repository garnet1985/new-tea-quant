import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Autocomplete,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  fetchPostProcessAdapters,
  fetchPostProcessProcessors,
  getAdapterDisplayLabel,
  getAdapterRemark,
  getAdapterStatus,
  getAdapterStatusLabel,
  setPostProcessEnabled,
  updatePostProcessAdapters,
} from '../../api/postProcessApi';
import PageLayout from '../../views/pageLayout';
import NtqButton from '../../views/ntqButton';
import Message from '../../views/message';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../views/dataGridLoadingOverlay';
import NtqIcon from '../../views/ntqIcon';
import { showToast } from 'containers/toast';
import './postProcessPage.scss';

const AUTOCOMPLETE_SLOT_PROPS = {
  paper: { className: 'post-process-autocomplete-paper' },
  listbox: { className: 'post-process-autocomplete-listbox' },
};

function StepStatusLegend() {
  return (
    <Stack
      direction="row"
      spacing={2}
      flexWrap="wrap"
      useFlexGap
      className="post-process-legend"
      alignItems="center"
    >
      <Typography variant="caption" color="text.secondary">图例：</Typography>
      <Stack direction="row" spacing={0.75} alignItems="center">
        <span className="post-process-legend-swatch post-process-legend-swatch--live" />
        <Typography variant="caption">可用（可正常使用）</Typography>
      </Stack>
      <Stack direction="row" spacing={0.75} alignItems="center">
        <span className="post-process-legend-swatch post-process-legend-swatch--dry" />
        <Typography variant="caption">测试模式（配置已齐）</Typography>
      </Stack>
      <Stack direction="row" spacing={0.75} alignItems="center">
        <span className="post-process-legend-swatch post-process-legend-swatch--bad" />
        <Typography variant="caption">不可用（缺配置）</Typography>
      </Stack>
    </Stack>
  );
}

function StepStatusChip({ step, adaptersByName }) {
  const status = getAdapterStatus(step, adaptersByName);
  const label = step?.display_name
    || getAdapterDisplayLabel(step?.name || step, adaptersByName);
  const tipParts = [getAdapterStatusLabel(status)];
  if (step?.name) tipParts.push(step.name);
  const readinessMsg = String(step?.readiness?.message || '').trim();
  if (readinessMsg) tipParts.push(readinessMsg);
  else if (step?.validate_message) tipParts.push(step.validate_message);
  return (
    <Tooltip title={tipParts.filter(Boolean).join(' · ')}>
      <Chip
        size="small"
        label={label}
        className={`post-process-step-chip post-process-step-chip--${status}`}
        variant="outlined"
      />
    </Tooltip>
  );
}

function ProcessorEditDialog({
  open,
  processor,
  adapterOptions,
  onClose,
  onSaved,
}) {
  const [rows, setRows] = useState([]);
  const [addOption, setAddOption] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open || !processor) return;
    setRows(
      (processor.adapters || []).map((row) => ({
        name: row.name,
        display_name: row.display_name || row.name,
        depends_on: [...(row.depends_on || [])],
      })),
    );
    setAddOption(null);
    setError('');
  }, [open, processor]);

  const availableToAdd = useMemo(() => {
    const used = new Set(rows.map((r) => r.name));
    return (adapterOptions || []).filter((opt) => !used.has(opt.name));
  }, [adapterOptions, rows]);

  const labelByName = useMemo(() => {
    const map = {};
    (adapterOptions || []).forEach((opt) => {
      map[opt.name] = opt.display_name || opt.name;
    });
    rows.forEach((row) => {
      if (!map[row.name]) map[row.name] = row.display_name || row.name;
    });
    return map;
  }, [adapterOptions, rows]);

  const handleAdd = () => {
    const name = String(addOption?.name || '').trim();
    if (!name) return;
    setRows((prev) => [
      ...prev,
      {
        name,
        display_name: addOption.display_name || name,
        depends_on: [],
      },
    ]);
    setAddOption(null);
  };

  const handleRemove = (name) => {
    setRows((prev) => prev
      .filter((row) => row.name !== name)
      .map((row) => ({
        ...row,
        depends_on: (row.depends_on || []).filter((dep) => dep !== name),
      })));
  };

  const handleSave = async () => {
    if (!processor?.key) return;
    setSaving(true);
    setError('');
    const payload = {};
    rows.forEach((row) => {
      payload[row.name] = { depends_on: [...(row.depends_on || [])] };
    });
    try {
      const item = await updatePostProcessAdapters(processor.key, payload);
      showToast({ severity: 'success', message: '已保存方案步骤' });
      onSaved?.(item);
      onClose?.();
    } catch (err) {
      setError(String(err?.message || err || '保存失败'));
    } finally {
      setSaving(false);
    }
  };

  const peerNames = rows.map((row) => row.name);

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        编辑方案步骤 · {processor?.name || processor?.key || '—'}
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          添加或移除执行单元，并为每个步骤设置 depends_on（依赖）。执行顺序由依赖拓扑计算，不可拖拽排序。
        </Typography>
        {error ? <Message severity="error" className="post-process-edit-error">{error}</Message> : null}
        <Stack spacing={1.5}>
          {rows.map((row) => (
            <Paper key={row.name} variant="outlined" className="post-process-edit-row">
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1}
                alignItems={{ sm: 'center' }}
                justifyContent="space-between"
              >
                <Stack spacing={0.25}>
                  <Typography variant="subtitle2">
                    {row.display_name || labelByName[row.name] || row.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">{row.name}</Typography>
                </Stack>
                <IconButton
                  size="small"
                  aria-label={`移除 ${row.name}`}
                  onClick={() => handleRemove(row.name)}
                  disabled={saving}
                >
                  <NtqIcon name="delete" size={18} />
                </IconButton>
              </Stack>
              <Autocomplete
                multiple
                size="small"
                options={peerNames.filter((name) => name !== row.name)}
                value={row.depends_on || []}
                getOptionLabel={(name) => labelByName[name] || name}
                onChange={(_, value) => {
                  setRows((prev) => prev.map((item) => (
                    item.name === row.name
                      ? { ...item, depends_on: value }
                      : item
                  )));
                }}
                slotProps={AUTOCOMPLETE_SLOT_PROPS}
                renderInput={(params) => (
                  <TextField {...params} label="depends_on" placeholder="依赖的执行单元" />
                )}
                disabled={saving}
                sx={{ mt: 1 }}
              />
            </Paper>
          ))}
        </Stack>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }} alignItems="center">
          <Autocomplete
            size="small"
            sx={{ minWidth: 240, flex: 1 }}
            options={availableToAdd}
            value={addOption}
            getOptionLabel={(opt) => (opt ? `${opt.display_name || opt.name} (${opt.name})` : '')}
            isOptionEqualToValue={(a, b) => a?.name === b?.name}
            onChange={(_, value) => setAddOption(value)}
            slotProps={AUTOCOMPLETE_SLOT_PROPS}
            renderInput={(params) => (
              <TextField {...params} label="添加执行单元" placeholder="选择执行单元" />
            )}
            disabled={saving || availableToAdd.length === 0}
          />
          <NtqButton onClick={handleAdd} disabled={saving || !addOption}>
            添加
          </NtqButton>
        </Stack>
      </DialogContent>
      <DialogActions>
        <NtqButton variant="ghost" onClick={onClose} disabled={saving}>取消</NtqButton>
        <NtqButton onClick={handleSave} disabled={saving}>
          {saving ? '保存中…' : '保存'}
        </NtqButton>
      </DialogActions>
    </Dialog>
  );
}

function PostProcessPage() {
  const [adapters, setAdapters] = useState([]);
  const [processors, setProcessors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pageReady, setPageReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [togglingKey, setTogglingKey] = useState('');
  const [editTarget, setEditTarget] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [adapterRes, processorRes] = await Promise.all([
        fetchPostProcessAdapters(),
        fetchPostProcessProcessors(),
      ]);
      setAdapters(adapterRes.data || []);
      setProcessors(processorRes.data || []);
    } catch (err) {
      setAdapters([]);
      setProcessors([]);
      setLoadError(String(err?.message || err || '加载失败'));
    } finally {
      setLoading(false);
      setPageReady(true);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const adapterOptions = useMemo(
    () => adapters.map((row) => ({
      name: row.name,
      display_name: row.display_name || row.name,
    })),
    [adapters],
  );

  const adaptersByName = useMemo(() => {
    const map = {};
    adapters.forEach((row) => {
      map[row.name] = row;
    });
    return map;
  }, [adapters]);

  const handleToggle = useCallback(async (row, enabled) => {
    const key = row.key;
    setTogglingKey(key);
    try {
      const item = await setPostProcessEnabled(key, enabled);
      setProcessors((prev) => prev.map((p) => (p.key === key ? item : p)));
      showToast({
        severity: 'success',
        message: enabled ? `已启用 ${item.name}` : `已禁用 ${item.name}`,
      });
    } catch (err) {
      showToast({
        severity: 'error',
        message: String(err?.message || err || '更新启用状态失败'),
      });
    } finally {
      setTogglingKey('');
    }
  }, []);

  const adapterColumns = useMemo(() => ([
    {
      field: 'display_name',
      headerName: '执行单元',
      flex: 1.1,
      minWidth: 160,
      renderCell: (params) => (
        <Stack spacing={0.25}>
          <Typography variant="body2" fontWeight={600}>
            {getAdapterDisplayLabel(params.row)}
          </Typography>
          <Typography variant="caption" color="text.secondary">{params.row.name}</Typography>
        </Stack>
      ),
    },
    {
      field: 'status',
      headerName: '状态',
      width: 120,
      renderCell: (params) => {
        const status = getAdapterStatus(params.row, adaptersByName);
        return (
          <Chip
            size="small"
            label={getAdapterStatusLabel(status)}
            className={`post-process-step-chip post-process-step-chip--${status}`}
            variant="outlined"
          />
        );
      },
    },
    {
      field: 'remark',
      headerName: '说明',
      flex: 1.4,
      minWidth: 200,
      sortable: false,
      renderCell: (params) => (
        <Typography variant="body2" color="text.secondary">
          {getAdapterRemark(params.row)}
        </Typography>
      ),
    },
  ]), [adaptersByName]);

  const processorColumns = useMemo(() => ([
    {
      field: 'name',
      headerName: '处理方案',
      flex: 1,
      minWidth: 140,
      renderCell: (params) => (
        <Stack spacing={0.25}>
          <Typography variant="body2" fontWeight={600}>{params.row.name}</Typography>
          <Typography variant="caption" color="text.secondary">{params.row.key}</Typography>
        </Stack>
      ),
    },
    {
      field: 'is_enabled',
      headerName: '启用',
      width: 100,
      renderCell: (params) => (
        <Switch
          size="small"
          checked={Boolean(params.row.is_enabled)}
          disabled={togglingKey === params.row.key}
          onChange={(e) => handleToggle(params.row, e.target.checked)}
          inputProps={{ 'aria-label': `启用 ${params.row.key}` }}
        />
      ),
    },
    {
      field: 'adapters',
      headerName: '包含的执行步骤',
      flex: 1.6,
      minWidth: 260,
      sortable: false,
      renderCell: (params) => {
        const steps = params.row.adapters || [];
        if (!steps.length) return '—';
        return (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
            {steps.map((step) => (
              <StepStatusChip
                key={step.name}
                step={step}
                adaptersByName={adaptersByName}
              />
            ))}
          </Stack>
        );
      },
    },
    {
      field: 'execution_order',
      headerName: '执行序（计算）',
      flex: 1.2,
      minWidth: 180,
      sortable: false,
      renderCell: (params) => {
        if (params.row.order_error) {
          return (
            <Typography variant="caption" color="error">
              {params.row.order_error}
            </Typography>
          );
        }
        const order = params.row.execution_order || [];
        if (!order.length) return '—';
        return (
          <Typography variant="caption" color="text.secondary">
            {order
              .map((name) => getAdapterDisplayLabel(name, adaptersByName))
              .join(' → ')}
          </Typography>
        );
      },
    },
    {
      field: 'actions',
      headerName: '操作',
      width: 140,
      sortable: false,
      renderCell: (params) => (
        <NtqButton size="small" variant="glass" onClick={() => setEditTarget(params.row)}>
          编辑步骤
        </NtqButton>
      ),
    },
  ]), [adaptersByName, handleToggle, togglingKey]);

  return (
    <PageLayout
      className="post-process-page"
      breadcrumbsItems={[{ label: '高级功能' }]}
      breadcrumbsCurrent="后续处理"
      bannerTitle="后续处理"
      bannerDescription={(
        <>
          管理全局扫描后续处理：处理方案（PostProcessor）与执行单元（Adapter）。
          每个策略扫描结束后，会运行<strong>全部已启用</strong>的方案（非策略绑定）。
        </>
      )}
      loading={!pageReady}
      loadingMessage="正在加载后续处理…"
    >
      {loadError ? (
        <Message severity="error" className="post-process-alert">{loadError}</Message>
      ) : null}

      <Typography variant="h6" className="post-process-section-title">处理方案</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        userspace/extensions/post_process/post_processors/；启用后每个策略扫完都会跑。步骤依赖用 depends_on，执行序自动计算。
      </Typography>
      <StepStatusLegend />
      <Paper className="post-process-grid" elevation={0}>
        <DataGrid
          autoHeight
          rows={processors}
          columns={processorColumns}
          loading={loading}
          disableRowSelectionOnClick
          getRowHeight={() => 'auto'}
          pageSizeOptions={[10, 25]}
          initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
          localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
          slots={NTQ_DATA_GRID_LOADING_SLOTS}
          sx={{
            '& .MuiDataGrid-cell': { py: 1, alignItems: 'flex-start' },
          }}
        />
      </Paper>

      <Typography variant="h6" className="post-process-section-title">执行单元</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        userspace/extensions/post_process/adapters/；展示名来自 settings.py 的 display_name。颜色含义同上图例。
      </Typography>
      <StepStatusLegend />
      <Paper className="post-process-grid" elevation={0}>
        <DataGrid
          autoHeight
          rows={adapters}
          columns={adapterColumns}
          loading={loading}
          disableRowSelectionOnClick
          getRowHeight={() => 'auto'}
          pageSizeOptions={[10, 25]}
          initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
          localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
          slots={NTQ_DATA_GRID_LOADING_SLOTS}
          sx={{
            '& .MuiDataGrid-cell': { py: 1, alignItems: 'flex-start' },
          }}
        />
      </Paper>

      <ProcessorEditDialog
        open={Boolean(editTarget)}
        processor={editTarget}
        adapterOptions={adapterOptions}
        onClose={() => setEditTarget(null)}
        onSaved={(item) => {
          setProcessors((prev) => prev.map((p) => (p.key === item.key ? item : p)));
        }}
      />
    </PageLayout>
  );
}

export default PostProcessPage;
