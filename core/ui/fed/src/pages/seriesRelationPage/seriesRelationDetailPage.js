import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Link as RouterLink, useLocation, useNavigate, useParams } from 'react-router-dom';
import PageLayout from 'views/pageLayout';
import NtqButton from 'views/ntqButton';
import RainbowButton from 'views/rainbowButton';
import EditorFieldLabel from 'containers/editor/fields/editorFieldLabel';
import { showToast } from 'containers/toast';
import { fetchDataContractList } from 'api/dataContractApi';
import { fetchStrategyList } from 'api/strategyApi';
import {
  fetchSeriesRelationResults,
  fetchSeriesRelationScene,
  parseSeriesRelationKeyFromPath,
  runSeriesRelationScene,
  saveSeriesRelationScene,
} from 'api/seriesRelationApi';
import { SeriesEditForm, SeriesSummaryCard } from './seriesCard';
import SeriesRelationReport from './seriesRelationReport';
import {
  FILL_OPTIONS,
  MAX_SERIES,
  NORMALIZE_OPTIONS,
  buildChartOption,
  emptyDataKeySeries,
  emptySettings,
  normalizeSettings,
} from './seriesRelationConstants';
import './seriesRelationPage.scss';

function LabeledField({ label, tip = '', children, inline = false }) {
  if (inline) {
    return (
      <Stack
        direction="row"
        alignItems="center"
        spacing={1}
        className="ntq-srel-field ntq-srel-field--inline"
      >
        <EditorFieldLabel
          field={{ label, tooltip: tip || '' }}
          sx={{ mb: 0, flex: '0 0 auto', whiteSpace: 'nowrap' }}
        />
        <Box className="ntq-srel-field__control" flex={1} minWidth={0}>
          {children}
        </Box>
      </Stack>
    );
  }
  return (
    <div className="ntq-srel-field">
      <EditorFieldLabel field={{ label, tooltip: tip || '' }} />
      {children}
    </div>
  );
}

function SeriesRelationDetailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const keyFromPath = useMemo(
    () => parseSeriesRelationKeyFromPath(params['*'] || ''),
    [params],
  );

  const navState = location.state && typeof location.state === 'object' ? location.state : {};
  const [isNew, setIsNew] = useState(Boolean(navState.isNew));
  const [draft, setDraft] = useState(() => {
    if (navState.isNew && keyFromPath) {
      const base = emptySettings(keyFromPath);
      if (navState.display_name) base.meta.display_name = String(navState.display_name);
      return base;
    }
    return emptySettings(keyFromPath);
  });
  const [maxSeries, setMaxSeries] = useState(MAX_SERIES);

  const [dataKeyOptions, setDataKeyOptions] = useState([]);
  const [strategyOptions, setStrategyOptions] = useState([]);

  const [pageLoading, setPageLoading] = useState(!navState.isNew);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [results, setResults] = useState(null);
  const [editIndex, setEditIndex] = useState(null);
  const [editDraft, setEditDraft] = useState(null);

  const chartOption = useMemo(
    () => buildChartOption(results?.chart, { normalize: draft?.normalize || results?.meta?.normalize }),
    [results?.chart, results?.meta?.normalize, draft?.normalize],
  );

  const loadResults = useCallback(async (key) => {
    if (!key) {
      setResults(null);
      return;
    }
    try {
      const payload = await fetchSeriesRelationResults(key);
      setResults(payload);
    } catch {
      setResults(null);
    }
  }, []);

  const loadScene = useCallback(async (key) => {
    if (!key) return;
    setPageLoading(true);
    setActionError('');
    setLoadError('');
    try {
      const scene = await fetchSeriesRelationScene(key);
      setIsNew(false);
      setMaxSeries(scene.max_series || MAX_SERIES);
      setDraft(() => {
        const next = normalizeSettings(scene.settings, scene.key);
        next.series = (next.series || []).map((item, i) => ({
          ...item,
          __uid: item.__uid || `loaded_${scene.key}_${i}`,
        }));
        return next;
      });
      if (scene.has_results) {
        await loadResults(scene.key);
      } else {
        setResults(null);
      }
    } catch (err) {
      // 新建场景磁盘上还不存在 → 保持草稿
      if (navState.isNew || String(err?.message || '').includes('未找到')) {
        setIsNew(true);
        setDraft((prev) => {
          if (prev?.meta?.key === key) return prev;
          const base = emptySettings(key);
          if (navState.display_name) base.meta.display_name = String(navState.display_name);
          return base;
        });
        setResults(null);
      } else {
        setLoadError(err?.message || '加载场景失败');
      }
    } finally {
      setPageLoading(false);
    }
  }, [loadResults, navState.display_name, navState.isNew]);

  useEffect(() => {
    let alive = true;
    Promise.all([
      fetchDataContractList({ page: 1, limit: 500 }),
      fetchStrategyList(),
    ])
      .then(([contracts, strategies]) => {
        if (!alive) return;
        setDataKeyOptions((contracts.data || []).filter((c) => c.is_time_series));
        setStrategyOptions(
          (strategies.data || [])
            .filter((s) => s.key || s.path)
            .map((s) => {
              // 只用目录里的真实 display_name；勿把 path 填进 display_name
              const displayName = String(s.display_name || '').trim();
              return {
                id: s.id || s.key || s.path,
                key: s.key || s.path,
                path: s.path || s.key,
                display_name: displayName,
                category: s.category || '',
                description: typeof s.description === 'string' ? s.description : '',
              };
            }),
        );
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!keyFromPath) {
      navigate('/advanced/series-relation', { replace: true });
      return;
    }
    if (isNew) {
      setPageLoading(false);
      // 清掉 location.state，避免刷新后误判为新建
      if (navState.isNew) {
        navigate(location.pathname, { replace: true, state: null });
      }
      return;
    }
    loadScene(keyFromPath);
    // 仅随路由 key / 是否新建切换；loadScene 内部自洽
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyFromPath, isNew]);

  const patchGlobals = (partial) => {
    setDraft((prev) => ({ ...prev, ...partial }));
  };

  const patchRange = (partial) => {
    setDraft((prev) => ({
      ...prev,
      range: { ...prev.range, ...partial },
    }));
  };

  const updateSeriesAt = (index, nextItem) => {
    setDraft((prev) => {
      const series = [...(prev.series || [])];
      const prevUid = series[index]?.__uid;
      series[index] = prevUid ? { ...nextItem, __uid: prevUid } : nextItem;
      return { ...prev, series };
    });
  };

  const removeSeriesAt = (index) => {
    setDraft((prev) => {
      const series = [...(prev.series || [])];
      if (series.length <= 1) return prev;
      series.splice(index, 1);
      return { ...prev, series };
    });
  };

  const addSeries = () => {
    const series = draft?.series || [];
    if (series.length >= maxSeries) return;
    const nextItem = {
      ...emptyDataKeySeries(),
      __uid: `s${Date.now().toString(36)}_${series.length}`,
    };
    const nextIndex = series.length;
    setDraft((prev) => ({
      ...prev,
      series: [...(prev.series || []), nextItem],
    }));
    setEditIndex(nextIndex);
    setEditDraft(nextItem);
  };

  const openEdit = (index) => {
    const item = draft?.series?.[index];
    if (!item) return;
    setEditIndex(index);
    setEditDraft({ ...item });
  };

  const closeEdit = () => {
    setEditIndex(null);
    setEditDraft(null);
  };

  const confirmEdit = () => {
    if (editIndex == null || !editDraft) {
      closeEdit();
      return;
    }
    updateSeriesAt(editIndex, editDraft);
    closeEdit();
  };

  const buildPayload = () => {
    const key = String(draft?.meta?.key || keyFromPath || '').trim();
    const series = (draft.series || []).map((item) => {
      if (!item || typeof item !== 'object') return item;
      const { __uid, ...rest } = item;
      return rest;
    });
    return {
      key,
      settings: {
        ...draft,
        series,
        meta: {
          ...draft.meta,
          key,
          display_name: String(draft.meta.display_name || '').trim() || key,
        },
      },
    };
  };

  const handleSave = async () => {
    const { key, settings } = buildPayload();
    if (!key) {
      showToast({ severity: 'error', content: '缺少 meta.key' });
      return;
    }
    setSaving(true);
    setActionError('');
    try {
      await saveSeriesRelationScene(key, settings);
      showToast({ severity: 'success', content: '已保存' });
      setIsNew(false);
      await loadScene(key);
    } catch (err) {
      const extras = Array.isArray(err?.payload?.errors)
        ? err.payload.errors.filter(Boolean).join('\n')
        : '';
      const msg = [err?.message || '保存失败', extras].filter(Boolean).join('\n');
      setActionError(msg);
      showToast({ severity: 'error', content: err?.message || '保存失败' });
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    const { key, settings } = buildPayload();
    if (!key) {
      showToast({ severity: 'error', content: '缺少场景 key' });
      return;
    }
    setRunning(true);
    setActionError('');
    try {
      await saveSeriesRelationScene(key, settings);
      const runResult = await runSeriesRelationScene(key);
      if (runResult?.success === false) {
        throw new Error(runResult.error || '跑批失败');
      }
      showToast({ severity: 'success', content: '跑批完成' });
      setIsNew(false);
      await loadResults(key);
    } catch (err) {
      const msg = err?.message || '跑批失败';
      setActionError(msg);
      showToast({ severity: 'error', content: msg });
    } finally {
      setRunning(false);
    }
  };

  const seriesCount = draft?.series?.length || 0;
  const canAdd = seriesCount < maxSeries;
  const hasResults = Boolean(results?.has_results);
  const busy = saving || running || pageLoading;
  const displayName = draft?.meta?.display_name || keyFromPath;
  const sceneKey = draft?.meta?.key || keyFromPath;

  return (
    <PageLayout
      className="ntq-srel-page"
      breadcrumbsItems={[
        { label: '高级功能', to: '/advanced/tags' },
        { label: '序列关系', to: '/advanced/series-relation' },
      ]}
      breadcrumbsCurrent={displayName}
      bannerTitle={displayName}
      bannerDescription={isNew ? `新建场景 · ${sceneKey}` : `key: ${sceneKey}`}
      bannerRightSlot={(
        <NtqButton
          variant="glass"
          icon="arrowBack"
          component={RouterLink}
          to="/advanced/series-relation"
        >
          返回列表
        </NtqButton>
      )}
      loading={pageLoading}
      loadingMessage="正在加载场景…"
    >
      {loadError ? (
        <Alert severity="error" sx={{ mb: 1.5 }}>{loadError}</Alert>
      ) : null}
      {actionError ? (
        <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setActionError('')}>
          {actionError}
        </Alert>
      ) : null}

      <Stack spacing={1.5} className="ntq-srel-page__stack">
        {/* 全局时间 / 归一化 + 保存 */}
        <Box className="ntq-srel-topbar">
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1.5}
            alignItems={{ xs: 'stretch', sm: 'center' }}
            className="ntq-srel-globals"
            flexWrap="wrap"
            useFlexGap
          >
            <LabeledField label="开始日期" inline>
              <TextField
                size="small"
                placeholder="YYYYMMDD"
                value={draft.range.start_date || ''}
                onChange={(e) => patchRange({ start_date: e.target.value.trim() })}
                fullWidth
              />
            </LabeledField>
            <LabeledField label="结束日期" inline>
              <TextField
                size="small"
                placeholder="可空"
                value={draft.range.end_date || ''}
                onChange={(e) => patchRange({ end_date: e.target.value.trim() })}
                fullWidth
              />
            </LabeledField>
            <LabeledField label="Normalize" inline>
              <Select
                size="small"
                fullWidth
                value={draft.normalize || 'zscore'}
                onChange={(e) => patchGlobals({ normalize: e.target.value })}
              >
                {NORMALIZE_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </LabeledField>
            <LabeledField label="Fill" inline>
              <Select
                size="small"
                fullWidth
                value={draft.fill || 'none'}
                onChange={(e) => patchGlobals({ fill: e.target.value })}
              >
                {FILL_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </LabeledField>
            <FormControlLabel
              className="ntq-srel-globals__analyze"
              control={(
                <Checkbox
                  checked={draft.analyze !== false}
                  onChange={(e) => patchGlobals({ analyze: e.target.checked })}
                  size="small"
                />
              )}
              label="生成分析报告"
            />
            <NtqButton
              variant="primary"
              disabled={busy}
              onClick={handleSave}
              className="ntq-srel-save-btn"
            >
              {saving ? '保存中…' : '保存'}
            </NtqButton>
          </Stack>
        </Box>

        {/* 系列摘要卡片（编辑弹窗） */}
        <Box className="ntq-srel-panel">
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            spacing={1}
            sx={{ mb: 1.25 }}
          >
            <Typography variant="subtitle2">
              系列（最多 {maxSeries}）
            </Typography>
            <NtqButton
              size="small"
              variant="primary"
              icon="add"
              disabled={!canAdd || busy}
              onClick={addSeries}
            >
              追加系列
            </NtqButton>
          </Stack>
          <div className="ntq-srel-summary-grid">
            {(draft.series || []).map((item, index) => (
              <SeriesSummaryCard
                key={item.__uid || `srel-sum-${index}`}
                index={index}
                value={item}
                onEdit={() => openEdit(index)}
                onRemove={() => removeSeriesAt(index)}
                canRemove={(draft.series || []).length > 1}
                strategyOptions={strategyOptions}
              />
            ))}
          </div>
        </Box>

        {/* 全宽：执行 + 报告（含矩阵与走势） */}
        <Box className="ntq-srel-exec">
          <Typography variant="subtitle2" className="ntq-srel-exec__title">
            执行
          </Typography>
          <Box className="ntq-srel-exec__body">
            <Stack direction="row" spacing={1.25} alignItems="center" className="ntq-srel-exec__actions">
              <RainbowButton
                shape="pill"
                icon={hasResults ? 'refresh' : 'play'}
                shimmer
                disabled={busy || !sceneKey}
                onClick={handleRun}
              >
                {running ? '运行中…' : (hasResults ? '重新跑批' : '开始跑批')}
              </RainbowButton>
            </Stack>
            <Box className="ntq-srel-exec__status">
              <Typography variant="body2">
                {running
                  ? '正在跑批…'
                  : hasResults
                    ? '已有结果，可查看下方报告'
                    : '尚未跑批'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                运行前会自动保存当前配置
              </Typography>
            </Box>
          </Box>
        </Box>

        <Box className="ntq-srel-panel ntq-srel-panel--report">
          <SeriesRelationReport
            results={results}
            chartOption={chartOption}
            strategyOptions={strategyOptions}
          />
        </Box>
      </Stack>

      <Dialog
        open={editIndex != null && editDraft != null}
        onClose={closeEdit}
        fullWidth
        maxWidth="sm"
        className="ntq-srel-edit-dialog"
      >
        <DialogTitle>
          编辑系列 {(editIndex == null ? 0 : editIndex) + 1}
        </DialogTitle>
        <DialogContent dividers>
          {editDraft ? (
            <Box sx={{ pt: 0.5 }}>
              <SeriesEditForm
                value={editDraft}
                onChange={setEditDraft}
                dataKeyOptions={dataKeyOptions}
                strategyOptions={strategyOptions}
              />
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions>
          <NtqButton variant="ghost" onClick={closeEdit}>取消</NtqButton>
          <NtqButton variant="primary" onClick={confirmEdit}>完成</NtqButton>
        </DialogActions>
      </Dialog>
    </PageLayout>
  );
}

export default SeriesRelationDetailPage;
