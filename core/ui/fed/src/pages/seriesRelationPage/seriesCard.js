import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Button,
  SearchSelect,
  Section,
  Select,
  TextField,
} from 'ui';
import { fetchStrategyVersions } from 'api/strategyApi';
import {
  LAYER_METRICS,
  LAYER_OPTIONS,
  TRANSFORM_OPTIONS,
  emptyDataKeySeries,
  emptyStrategySimSeries,
  findStrategyOption,
  previewWho,
} from './seriesRelationConstants';

const SOURCE_OPTIONS = [
  { value: 'data_key', label: '行情 / 宏观契约' },
  { value: 'strategy_sim', label: '策略回测' },
];

/** 弹窗内系列编辑表单（无手风琴外壳）。 */
export function SeriesEditForm({
  value,
  onChange,
  dataKeyOptions = [],
  strategyOptions = [],
}) {
  const [versionOptions, setVersionOptions] = useState(['latest']);
  const [versionsLoading, setVersionsLoading] = useState(false);

  const source = value?.source === 'strategy_sim' ? 'strategy_sim' : 'data_key';
  const selectedContract = useMemo(
    () => dataKeyOptions.find((o) => o.key === value?.data_key) || null,
    [dataKeyOptions, value?.data_key],
  );
  const needsEntity = source === 'data_key'
    ? Boolean(selectedContract?.is_per_entity)
    : value?.layer === 'price';

  const metricOptions = LAYER_METRICS[value?.layer] || LAYER_METRICS.portfolio;

  const dataKeySelectOptions = useMemo(
    () => dataKeyOptions.map((o) => ({
      value: o.key,
      label: o.display_name || o.key,
    })),
    [dataKeyOptions],
  );

  const strategySelectOptions = useMemo(() => {
    const opts = strategyOptions.map((o) => ({
      value: o.key || o.path,
      label: o.display_name || o.key || o.path,
    }));
    const key = String(value?.strategy_key || '').trim();
    if (key && !opts.some((o) => o.value === key)) {
      opts.unshift({ value: key, label: key });
    }
    return opts;
  }, [strategyOptions, value?.strategy_key]);

  const versionSelectOptions = useMemo(() => {
    const opts = versionOptions.map((ver) => ({ value: ver, label: ver }));
    const current = String(value?.version || '').trim();
    if (current && !opts.some((o) => o.value === current)) {
      opts.push({ value: current, label: current });
    }
    return opts;
  }, [value?.version, versionOptions]);

  useEffect(() => {
    if (source !== 'strategy_sim') return undefined;
    const sk = String(value?.strategy_key || '').trim();
    if (!sk) {
      setVersionOptions(['latest']);
      return undefined;
    }
    let alive = true;
    setVersionsLoading(true);
    fetchStrategyVersions(sk)
      .then((res) => {
        if (!alive) return;
        const ids = (res.versions || [])
          .map((v) => String(v.version_id || '').trim())
          .filter(Boolean);
        setVersionOptions(['latest', ...ids.filter((id) => id !== 'latest')]);
      })
      .catch(() => {
        if (alive) setVersionOptions(['latest']);
      })
      .finally(() => {
        if (alive) setVersionsLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [source, value?.strategy_key]);

  const patch = (partial) => onChange({ ...value, ...partial });

  const handleSourceChange = (nextSource) => {
    if (nextSource === 'strategy_sim') {
      onChange(emptyStrategySimSeries());
    } else {
      onChange(emptyDataKeySeries());
    }
  };

  const handleLayerChange = (layer) => {
    const metrics = LAYER_METRICS[layer] || LAYER_METRICS.portfolio;
    patch({
      layer,
      metric: metrics[0].value,
      entity_id: layer === 'portfolio' ? '' : value.entity_id,
    });
  };

  return (
    <Section gap="md" className="ntq-srel-card__body">
      <Select
        label="来源"
        tip="行情/宏观契约，或策略回测产物"
        value={source}
        onChange={(e) => handleSourceChange(e.target.value)}
        options={SOURCE_OPTIONS}
        maxWidth={false}
        surface="glass"
      />

      {source === 'data_key' ? (
        <>
          <SearchSelect
            label="DataKey"
            tip="仅 time_series 契约"
            value={value.data_key || ''}
            onChange={(e) => {
              const key = String(e.target.value || '').trim();
              const next = dataKeyOptions.find((o) => o.key === key);
              patch({
                data_key: key,
                entity_id: next?.is_per_entity ? value.entity_id : '',
              });
            }}
            options={dataKeySelectOptions}
            placeholder="搜索 time_series 契约…"
            emptyLabel="选择 time_series 契约"
            maxWidth={false}
            surface="glass"
          />
          <TextField
            label="Field"
            tip="如 close；可手输"
            value={value.field || ''}
            onChange={(e) => patch({ field: e.target.value.trim() })}
            placeholder="如 close"
            maxWidth={false}
            surface="glass"
          />
          {needsEntity ? (
            <TextField
              label="Entity ID"
              tip="股票或指数代码"
              value={value.entity_id || ''}
              onChange={(e) => patch({ entity_id: e.target.value.trim() })}
              placeholder="如 600016.SH"
              maxWidth={false}
              surface="glass"
            />
          ) : null}
        </>
      ) : (
        <>
          <SearchSelect
            label="Strategy Key"
            tip="策略 meta.key"
            value={
              findStrategyOption(value.strategy_key, strategyOptions)?.key
              || value.strategy_key
              || ''
            }
            onChange={(e) => {
              const key = String(e.target.value || '').trim();
              patch({ strategy_key: key, version: 'latest' });
            }}
            options={strategySelectOptions}
            placeholder="搜索策略…"
            emptyLabel="策略 meta.key"
            maxWidth={false}
            surface="glass"
          />
          <Select
            label="Layer"
            value={value.layer || 'portfolio'}
            onChange={(e) => handleLayerChange(e.target.value)}
            options={LAYER_OPTIONS}
            maxWidth={false}
            surface="glass"
          />
          <Select
            label="Metric"
            value={value.metric || metricOptions[0].value}
            onChange={(e) => patch({ metric: e.target.value })}
            options={metricOptions}
            maxWidth={false}
            surface="glass"
          />
          <Select
            label="Version"
            tip="默认 latest"
            value={value.version || 'latest'}
            disabled={versionsLoading}
            onChange={(e) => patch({ version: e.target.value })}
            options={versionSelectOptions}
            maxWidth={false}
            surface="glass"
          />
          {needsEntity ? (
            <TextField
              label="Entity ID"
              tip="price.cum_exit_roi 需要单票"
              value={value.entity_id || ''}
              onChange={(e) => patch({ entity_id: e.target.value.trim() })}
              placeholder="单票代码"
              maxWidth={false}
              surface="glass"
            />
          ) : null}
        </>
      )}

      <TextField
        label="Label"
        tip="图表与报告显示名，可空"
        value={value.label || ''}
        onChange={(e) => patch({ label: e.target.value })}
        placeholder="可选"
        maxWidth={false}
        surface="glass"
      />
      <Select
        label="Transform"
        value={value.transform || (source === 'strategy_sim' ? 'returns' : 'none')}
        onChange={(e) => patch({ transform: e.target.value })}
        options={TRANSFORM_OPTIONS}
        maxWidth={false}
        surface="glass"
      />
    </Section>
  );
}

SeriesEditForm.propTypes = {
  value: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  dataKeyOptions: PropTypes.arrayOf(PropTypes.object),
  strategyOptions: PropTypes.arrayOf(PropTypes.object),
};

/** 顶栏下方的摘要卡片：title + more info。 */
export function SeriesSummaryCard({
  index,
  value,
  onEdit,
  onRemove,
  canRemove = true,
  strategyOptions = [],
}) {
  const titleLabel = String(value?.label || '').trim();
  const who = previewWho(value, strategyOptions);
  return (
    <div className="ntq-srel-summary-card">
      <div className="ntq-srel-summary-card__text">
        <div className="ntq-srel-summary-card__title">
          系列 {index + 1}
          {titleLabel ? ` · ${titleLabel}` : ''}
        </div>
        <div className="ntq-srel-summary-card__who ntq-muted">{who}</div>
      </div>
      <div className="ntq-srel-summary-card__actions">
        <Button size="small" variant="glass" onClick={onEdit}>
          编辑
        </Button>
        <Button
          variant="ghost"
          icon="trash"
          iconSize="sm"
          aria-label="删除系列"
          disabled={!canRemove}
          onClick={onRemove}
          className="ntq-srel-card__delete"
        />
      </div>
    </div>
  );
}

SeriesSummaryCard.propTypes = {
  index: PropTypes.number.isRequired,
  value: PropTypes.object.isRequired,
  onEdit: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  canRemove: PropTypes.bool,
  strategyOptions: PropTypes.arrayOf(PropTypes.object),
};

export default SeriesEditForm;
