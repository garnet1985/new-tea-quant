import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  Button,
  Checkbox,
  Dialog,
  Heading,
  Message,
  Section,
  Select,
  TextField,
} from 'ui';
import { showToast } from 'ui/message/toast';
import { PageLayout, RainbowButton } from 'ntq-ui';
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
      if (navState.isNew) {
        navigate(location.pathname, { replace: true, state: null });
      }
      return;
    }
    loadScene(keyFromPath);
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
      showToast({ status: 'error', content: '缺少 meta.key' });
      return;
    }
    setSaving(true);
    setActionError('');
    try {
      await saveSeriesRelationScene(key, settings);
      showToast({ status: 'success', content: '已保存' });
      setIsNew(false);
      await loadScene(key);
    } catch (err) {
      const extras = Array.isArray(err?.payload?.errors)
        ? err.payload.errors.filter(Boolean).join('\n')
        : '';
      const msg = [err?.message || '保存失败', extras].filter(Boolean).join('\n');
      setActionError(msg);
      showToast({ status: 'error', content: err?.message || '保存失败' });
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    const { key, settings } = buildPayload();
    if (!key) {
      showToast({ status: 'error', content: '缺少场景 key' });
      return;
    }
    setRunning(true);
    setActionError('');
    try {
      await saveSeriesRelationScene(key, settings);
      const runResult = await runSeriesRelationScene(key);
      if (runResult?.success === false) {
        throw new Error(runResult.error || '计算失败');
      }
      showToast({ status: 'success', content: '计算完成' });
      setIsNew(false);
      await loadResults(key);
    } catch (err) {
      const msg = err?.message || '计算失败';
      setActionError(msg);
      showToast({ status: 'error', content: msg });
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
      bannerDescription={
        isNew
          ? `新建序列关系场景（${sceneKey}）`
          : `对比本场景中的多条序列（${sceneKey}）`
      }
      bannerRightSlot={(
        <Button
          variant="glass"
          icon="arrowBack"
          component={RouterLink}
          to="/advanced/series-relation"
        >
          返回列表
        </Button>
      )}
      loading={pageLoading}
      loadingMessage="正在加载场景…"
    >
      <Section className="ntq-srel-page__stack" gap="md">
        {loadError ? <Message status="error">{loadError}</Message> : null}
        {actionError ? (
          <Message status="error" onClose={() => setActionError('')}>
            {actionError}
          </Message>
        ) : null}

        <div className="ntq-srel-topbar" data-ntq-help="series-relation-detail-globals">
          <div className="ntq-srel-globals">
            <TextField
              label="开始日期"
              labelPlacement="inline"
              placeholder="YYYYMMDD"
              value={draft.range.start_date || ''}
              onChange={(e) => patchRange({ start_date: e.target.value.trim() })}
              maxWidth={false}
              surface="glass"
              className="ntq-srel-field--inline"
            />
            <TextField
              label="结束日期"
              labelPlacement="inline"
              placeholder="可空"
              value={draft.range.end_date || ''}
              onChange={(e) => patchRange({ end_date: e.target.value.trim() })}
              maxWidth={false}
              surface="glass"
              className="ntq-srel-field--inline"
            />
            <Select
              label="归一方式"
              labelPlacement="inline"
              value={draft.normalize || 'zscore'}
              onChange={(e) => patchGlobals({ normalize: e.target.value })}
              options={NORMALIZE_OPTIONS}
              maxWidth={false}
              surface="glass"
              className="ntq-srel-field--inline"
            />
            <Select
              label="缺失填充"
              labelPlacement="inline"
              value={draft.fill || 'none'}
              onChange={(e) => patchGlobals({ fill: e.target.value })}
              options={FILL_OPTIONS}
              maxWidth={false}
              surface="glass"
              className="ntq-srel-field--inline"
            />
            <Checkbox
              label="生成分析报告"
              checked={draft.analyze !== false}
              onChange={(e) => patchGlobals({ analyze: e.target.checked })}
              className="ntq-srel-globals__analyze"
            />
            <Button
              variant="primary"
              disabled={busy}
              onClick={handleSave}
              className="ntq-srel-save-btn"
            >
              {saving ? '保存中…' : '保存'}
            </Button>
          </div>
        </div>

        <Section
          className="ntq-srel-panel"
          gap="sm"
          data-ntq-help="series-relation-detail-series"
        >
          <div className="ntq-srel-panel__head">
            <Heading level="h4" gap="none">
              系列（最多 {maxSeries}）
            </Heading>
            <Button
              size="small"
              variant="primary"
              icon="add"
              disabled={!canAdd || busy}
              onClick={addSeries}
            >
              追加系列
            </Button>
          </div>
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
                dataKeyOptions={dataKeyOptions}
              />
            ))}
          </div>
        </Section>

        <div className="ntq-srel-exec" data-ntq-help="series-relation-detail-run">
          <Heading level="h4" gap="none" className="ntq-srel-exec__title">
            执行
          </Heading>
          <div className="ntq-srel-exec__body">
            <div className="ntq-srel-exec__actions">
              <RainbowButton
                shape="pill"
                icon={hasResults ? 'refresh' : 'play'}
                shimmer
                disabled={busy || !sceneKey}
                onClick={handleRun}
              >
                {running ? '计算中…' : (hasResults ? '重新计算' : '开始计算关系')}
              </RainbowButton>
            </div>
            <div className="ntq-srel-exec__status">
              <p className="ntq-srel-exec__status-main">
                {running
                  ? '正在计算…'
                  : hasResults
                    ? '已有结果，可查看下方报告'
                    : '尚未计算'}
              </p>
              <p className="ntq-muted ntq-srel-exec__status-hint">
                运行前会自动保存当前配置
              </p>
            </div>
          </div>
        </div>

        <Section className="ntq-srel-panel ntq-srel-panel--report" gap="md">
          <SeriesRelationReport
            results={results}
            chartOption={chartOption}
            strategyOptions={strategyOptions}
            dataKeyOptions={dataKeyOptions}
          />
        </Section>
      </Section>

      <Dialog
        open={editIndex != null && editDraft != null}
        onClose={closeEdit}
        title={`编辑系列 ${(editIndex == null ? 0 : editIndex) + 1}`}
        size="sm"
        className="ntq-srel-edit-dialog"
        actions={(
          <>
            <Button variant="ghost" onClick={closeEdit}>取消</Button>
            <Button variant="primary" onClick={confirmEdit}>完成</Button>
          </>
        )}
      >
        {editDraft ? (
          <SeriesEditForm
            value={editDraft}
            onChange={setEditDraft}
            dataKeyOptions={dataKeyOptions}
            strategyOptions={strategyOptions}
          />
        ) : null}
      </Dialog>
    </PageLayout>
  );
}

export default SeriesRelationDetailPage;
