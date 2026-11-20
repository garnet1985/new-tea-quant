import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Autocomplete,
  Button,
  DataGrid,
  Dialog,
  Heading,
  Message,
  SearchSelect,
  Section,
  Switch,
  Tag,
} from 'ui';
import { showToast } from 'ui/message/toast';
import { PageLayout } from 'ntq-ui';
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
import './postProcessPage.scss';

/** 状态列：一律实心，色区分可用性 */
function statusColumnTag(status) {
  const key = String(status || '');
  if (key === 'live') return { status: 'success', variant: 'solid' };
  if (key === 'dry_run') return { status: 'warning', variant: 'solid' };
  return { status: 'error', variant: 'solid' };
}

/** 步骤名 Tag：一律实心，色区分可用性 */
function stepTagProps(status) {
  const key = String(status || '');
  if (key === 'live') return { status: 'success', variant: 'solid' };
  if (key === 'dry_run') return { status: 'warning', variant: 'solid' };
  return { status: 'error', variant: 'solid' };
}

function StepStatusLegend() {
  return (
    <div className="post-process-legend">
      <span className="ntq-muted">图例：</span>
      <span className="post-process-legend__item">
        <span className="post-process-legend-swatch post-process-legend-swatch--live" />
        可用（可正常使用）
      </span>
      <span className="post-process-legend__item">
        <span className="post-process-legend-swatch post-process-legend-swatch--dry" />
        测试模式（配置已齐）
      </span>
      <span className="post-process-legend__item">
        <span className="post-process-legend-swatch post-process-legend-swatch--bad" />
        不可用（缺配置）
      </span>
    </div>
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
  const tag = stepTagProps(status);
  return (
    <span title={tipParts.filter(Boolean).join(' · ')} className="post-process-step-chip-wrap">
      <Tag
        status={tag.status}
        variant={tag.variant}
        className={`post-process-step-chip post-process-step-chip--${status}`}
      >
        {label}
      </Tag>
    </span>
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
  const [addName, setAddName] = useState('');
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
    setAddName('');
    setError('');
  }, [open, processor]);

  const availableToAdd = useMemo(() => {
    const used = new Set(rows.map((r) => r.name));
    return (adapterOptions || []).filter((opt) => !used.has(opt.name));
  }, [adapterOptions, rows]);

  const addOptions = useMemo(
    () => availableToAdd.map((opt) => ({
      value: opt.name,
      label: `${opt.display_name || opt.name} (${opt.name})`,
    })),
    [availableToAdd],
  );

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
    const name = String(addName || '').trim();
    if (!name) return;
    const hit = availableToAdd.find((opt) => opt.name === name);
    setRows((prev) => [
      ...prev,
      {
        name,
        display_name: hit?.display_name || name,
        depends_on: [],
      },
    ]);
    setAddName('');
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
      showToast({ status: 'success', content: '已保存方案步骤' });
      onSaved?.(item);
      onClose?.();
    } catch (err) {
      setError(String(err?.message || err || '保存失败'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={saving ? undefined : onClose}
      title={`编辑方案步骤 · ${processor?.name || processor?.key || '—'}`}
      size="lg"
      actions={(
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>取消</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </Button>
        </>
      )}
    >
      <Section gap="md" className="post-process-edit">
        <p className="ntq-muted">
          添加或移除执行单元，并为每个步骤设置依赖。执行顺序由依赖关系自动计算，不可拖拽排序。
        </p>
        {error ? <Message status="error">{error}</Message> : null}

        {rows.map((row) => {
          const depOptions = rows
            .filter((item) => item.name !== row.name)
            .map((item) => ({
              value: item.name,
              label: labelByName[item.name] || item.name,
            }));
          return (
            <div key={row.name} className="post-process-edit-row">
              <div className="post-process-edit-row__head">
                <div className="post-process-edit-row__meta">
                  <strong>{row.display_name || labelByName[row.name] || row.name}</strong>
                  <span className="ntq-muted">{row.name}</span>
                </div>
                <Button
                  variant="ghost"
                  icon="trash"
                  iconSize="sm"
                  aria-label={`移除 ${row.name}`}
                  onClick={() => handleRemove(row.name)}
                  disabled={saving}
                  className="post-process-edit-row__remove"
                />
              </div>
              <Autocomplete
                multiple
                label="依赖"
                tip="依赖的执行单元"
                options={depOptions}
                value={row.depends_on || []}
                onChange={(e) => {
                  const next = Array.isArray(e.target.value) ? e.target.value : [];
                  setRows((prev) => prev.map((item) => (
                    item.name === row.name
                      ? { ...item, depends_on: next }
                      : item
                  )));
                }}
                placeholder="依赖的执行单元"
                disabled={saving}
                maxWidth={false}
                surface="glass"
              />
            </div>
          );
        })}

        <div className="post-process-edit-add">
          <SearchSelect
            label="添加执行单元"
            value={addName}
            onChange={(e) => setAddName(String(e.target.value || ''))}
            options={addOptions}
            placeholder="选择执行单元"
            emptyLabel="选择执行单元"
            disabled={saving || availableToAdd.length === 0}
            maxWidth={false}
            surface="glass"
          />
          <Button
            variant="glass"
            onClick={handleAdd}
            disabled={saving || !addName}
          >
            添加
          </Button>
        </div>
      </Section>
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
        status: 'success',
        content: enabled ? `已启用 ${item.name}` : `已禁用 ${item.name}`,
      });
    } catch (err) {
      showToast({
        status: 'error',
        content: String(err?.message || err || '更新启用状态失败'),
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
        <div className="post-process-cell-stack">
          <span className="post-process-cell-name">{getAdapterDisplayLabel(params.row)}</span>
          <span className="ntq-muted post-process-cell-key">{params.row.name}</span>
        </div>
      ),
    },
    {
      field: 'status',
      headerName: '状态',
      width: 120,
      renderCell: (params) => {
        const status = getAdapterStatus(params.row, adaptersByName);
        const tag = statusColumnTag(status);
        return (
          <Tag
            status={tag.status}
            variant={tag.variant}
            className={`post-process-step-chip post-process-step-chip--${status}`}
          >
            {getAdapterStatusLabel(status)}
          </Tag>
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
        <span className="ntq-muted">{getAdapterRemark(params.row)}</span>
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
        <div className="post-process-cell-stack">
          <span className="post-process-cell-name">{params.row.name}</span>
          <span className="ntq-muted post-process-cell-key">{params.row.key}</span>
        </div>
      ),
    },
    {
      field: 'is_enabled',
      headerName: '启用',
      width: 100,
      renderCell: (params) => (
        <span data-ntq-help="post-process-enabled">
          <Switch
            checked={Boolean(params.row.is_enabled)}
            disabled={togglingKey === params.row.key}
            onChange={(e) => handleToggle(params.row, e.target.checked)}
            aria-label={`启用 ${params.row.key}`}
          />
        </span>
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
        if (!steps.length) {
          return <span data-ntq-help="post-process-steps">—</span>;
        }
        return (
          <div className="post-process-step-list" data-ntq-help="post-process-steps">
            {steps.map((step) => (
              <StepStatusChip
                key={step.name}
                step={step}
                adaptersByName={adaptersByName}
              />
            ))}
          </div>
        );
      },
    },
    {
      field: 'execution_order',
      headerName: '执行顺序',
      flex: 1.2,
      minWidth: 180,
      sortable: false,
      renderCell: (params) => {
        if (params.row.order_error) {
          return (
            <span className="post-process-order-error">{params.row.order_error}</span>
          );
        }
        const order = params.row.execution_order || [];
        if (!order.length) return '—';
        return (
          <span className="ntq-muted post-process-order">
            {order
              .map((name) => getAdapterDisplayLabel(name, adaptersByName))
              .join(' → ')}
          </span>
        );
      },
    },
    {
      field: 'actions',
      headerName: '操作',
      width: 88,
      sortable: false,
      align: 'left',
      headerAlign: 'left',
      cellClassName: 'post-process-cell--actions',
      renderCell: (params) => (
        <button
          type="button"
          className="post-process-edit-link"
          onClick={() => setEditTarget(params.row)}
        >
          编辑步骤
        </button>
      ),
    },
  ]), [adaptersByName, handleToggle, togglingKey]);

  return (
    <PageLayout
      className="post-process-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="后续处理"
      bannerTitle="后续处理"
      bannerDescription="定义策略选股结束后的全局后续动作，例如通知、过滤或接入机器学习。"
      loading={!pageReady}
      loadingMessage="正在加载后续处理…"
    >
      <Section className="post-process-page__stack" gap="md">
        {loadError ? <Message status="error">{loadError}</Message> : null}

        <Section className="post-process-panel" gap="lg">
          <Section
            className="post-process-block"
            gap="sm"
            data-ntq-help="post-process-schemes"
          >
            <Heading level="h3" gap="none">处理方案</Heading>
            <p className="ntq-muted post-process-block__desc">
              方案存放在用户扩展目录中。启用后，每次策略扫描结束都会执行。步骤按依赖自动排序。
            </p>
            <StepStatusLegend />
            <DataGrid
              autoHeight
              rows={processors}
              columns={processorColumns}
              loading={loading}
              getRowHeight={() => 'auto'}
              pageSizeOptions={[10, 25]}
              initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
              cellLayout="wrap"
            />
          </Section>

          <Section
            className="post-process-block"
            gap="sm"
            data-ntq-help="post-process-adapters"
          >
            <Heading level="h3" gap="none">执行单元</Heading>
            <p className="ntq-muted post-process-block__desc">
              执行单元来自用户扩展；列表展示名为各单元配置中的显示名。颜色含义见上方图例。
            </p>
            <StepStatusLegend />
            <DataGrid
              autoHeight
              rows={adapters}
              columns={adapterColumns}
              loading={loading}
              getRowHeight={() => 'auto'}
              pageSizeOptions={[10, 25]}
              initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
              cellLayout="wrap"
            />
          </Section>
        </Section>
      </Section>

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
