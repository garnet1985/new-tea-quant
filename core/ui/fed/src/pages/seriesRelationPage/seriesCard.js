import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  IconButton,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import Autocomplete from '@mui/material/Autocomplete';
import EditorFieldLabel from 'containers/editor/fields/editorFieldLabel';
import Icon from 'views/ntqIcon';
import Button from 'views/ntqButton';
import { fetchStrategyVersions } from 'api/strategyApi';
import {
  COMMON_FIELDS,
  LAYER_METRICS,
  LAYER_OPTIONS,
  TRANSFORM_OPTIONS,
  emptyDataKeySeries,
  emptyStrategySimSeries,
  findStrategyOption,
  previewWho,
} from './seriesRelationConstants';

const AUTOCOMPLETE_SLOTS = {
  popper: {
    sx: { zIndex: 1500 },
  },
};

function LabeledField({ label, tip = '', children }) {
  return (
    <div className="ntq-srel-field">
      <EditorFieldLabel field={{ label, tooltip: tip || '' }} />
      {children}
    </div>
  );
}

LabeledField.propTypes = {
  label: PropTypes.string.isRequired,
  tip: PropTypes.string,
  children: PropTypes.node.isRequired,
};

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
    <Stack spacing={1.5} className="ntq-srel-card__body">
      <LabeledField label="来源" tip="行情/宏观契约，或策略回测产物">
        <Select
          size="small"
          fullWidth
          value={source}
          onChange={(e) => handleSourceChange(e.target.value)}
        >
          <MenuItem value="data_key">行情 / 宏观契约</MenuItem>
          <MenuItem value="strategy_sim">策略回测</MenuItem>
        </Select>
      </LabeledField>

      {source === 'data_key' ? (
        <>
          <LabeledField label="DataKey" tip="仅 time_series 契约">
            <Autocomplete
              size="small"
              options={dataKeyOptions}
              value={selectedContract}
              getOptionLabel={(o) => (typeof o === 'string' ? o : (o.display_name || o.key || ''))}
              isOptionEqualToValue={(a, b) => a?.key === b?.key}
              slotProps={AUTOCOMPLETE_SLOTS}
              onChange={(_e, next) => {
                if (typeof next === 'string') {
                  patch({ data_key: next.trim(), entity_id: value.entity_id });
                  return;
                }
                patch({
                  data_key: next?.key || '',
                  entity_id: next?.is_per_entity ? value.entity_id : '',
                });
              }}
              renderInput={(params) => (
                <TextField {...params} placeholder="选择 time_series 契约" />
              )}
            />
          </LabeledField>
          <LabeledField label="Field" tip="如 close；可手输">
            <Autocomplete
              size="small"
              freeSolo
              options={COMMON_FIELDS}
              value={value.field || ''}
              slotProps={AUTOCOMPLETE_SLOTS}
              onChange={(_e, next) => patch({ field: String(next || '').trim() })}
              onInputChange={(_e, next, reason) => {
                if (reason === 'input' || reason === 'clear') {
                  patch({ field: String(next || '').trim() });
                }
              }}
              renderInput={(params) => (
                <TextField {...params} placeholder="如 close" />
              )}
            />
          </LabeledField>
          {needsEntity ? (
            <LabeledField label="Entity ID" tip="股票或指数代码">
              <TextField
                size="small"
                value={value.entity_id || ''}
                onChange={(e) => patch({ entity_id: e.target.value.trim() })}
                placeholder="如 600016.SH"
                fullWidth
              />
            </LabeledField>
          ) : null}
        </>
      ) : (
        <>
          <LabeledField label="Strategy Key" tip="策略 meta.key">
            <Autocomplete
              size="small"
              freeSolo
              options={strategyOptions}
              value={
                findStrategyOption(value.strategy_key, strategyOptions)
                || (value.strategy_key
                  ? { key: value.strategy_key, display_name: value.strategy_key }
                  : null)
              }
              getOptionLabel={(o) => (typeof o === 'string' ? o : (o.display_name || o.key || ''))}
              isOptionEqualToValue={(a, b) => a?.key === b?.key}
              slotProps={AUTOCOMPLETE_SLOTS}
              onChange={(_e, next) => {
                const key = typeof next === 'string'
                  ? next.trim()
                  : String(next?.key || '').trim();
                patch({ strategy_key: key, version: 'latest' });
              }}
              renderInput={(params) => (
                <TextField {...params} placeholder="策略 meta.key" />
              )}
            />
          </LabeledField>
          <LabeledField label="Layer">
            <Select
              size="small"
              fullWidth
              value={value.layer || 'portfolio'}
              onChange={(e) => handleLayerChange(e.target.value)}
            >
              {LAYER_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
              ))}
            </Select>
          </LabeledField>
          <LabeledField label="Metric">
            <Select
              size="small"
              fullWidth
              value={value.metric || metricOptions[0].value}
              onChange={(e) => patch({ metric: e.target.value })}
            >
              {metricOptions.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
              ))}
            </Select>
          </LabeledField>
          <LabeledField label="Version" tip="默认 latest">
            <Select
              size="small"
              fullWidth
              value={value.version || 'latest'}
              disabled={versionsLoading}
              onChange={(e) => patch({ version: e.target.value })}
            >
              {versionOptions.map((ver) => (
                <MenuItem key={ver} value={ver}>{ver}</MenuItem>
              ))}
              {value.version && !versionOptions.includes(value.version) ? (
                <MenuItem value={value.version}>{value.version}</MenuItem>
              ) : null}
            </Select>
          </LabeledField>
          {needsEntity ? (
            <LabeledField label="Entity ID" tip="price.cum_exit_roi 需要单票">
              <TextField
                size="small"
                value={value.entity_id || ''}
                onChange={(e) => patch({ entity_id: e.target.value.trim() })}
                placeholder="单票代码"
                fullWidth
              />
            </LabeledField>
          ) : null}
        </>
      )}

      <LabeledField label="Label" tip="图表与报告显示名，可空">
        <TextField
          size="small"
          value={value.label || ''}
          onChange={(e) => patch({ label: e.target.value })}
          placeholder="可选"
          fullWidth
        />
      </LabeledField>
      <LabeledField label="Transform">
        <Select
          size="small"
          fullWidth
          value={value.transform || (source === 'strategy_sim' ? 'returns' : 'none')}
          onChange={(e) => patch({ transform: e.target.value })}
        >
          {TRANSFORM_OPTIONS.map((opt) => (
            <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
          ))}
        </Select>
      </LabeledField>
    </Stack>
  );
}

SeriesEditForm.propTypes = {
  value: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  dataKeyOptions: PropTypes.arrayOf(PropTypes.object),
  strategyOptions: PropTypes.arrayOf(PropTypes.object),
};

/** 顶栏下方的摘要卡片：title + more info（与契约源同 pattern）。 */
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
    <Box className="ntq-srel-summary-card">
      <Box className="ntq-srel-summary-card__text" minWidth={0}>
        <Typography variant="subtitle2" className="ntq-srel-summary-card__title">
          系列 {index + 1}
          {titleLabel ? ` · ${titleLabel}` : ''}
        </Typography>
        <Typography variant="caption" color="text.secondary" className="ntq-srel-summary-card__who">
          {who}
        </Typography>
      </Box>
      <Stack direction="row" spacing={0.5} alignItems="center" className="ntq-srel-summary-card__actions">
        <Button size="small" variant="glass" onClick={onEdit}>
          编辑
        </Button>
        <IconButton
          size="small"
          aria-label="删除系列"
          disabled={!canRemove}
          onClick={onRemove}
          className="ntq-srel-card__delete"
        >
          <Icon name="trash" size={18} tone="error" />
        </IconButton>
      </Stack>
    </Box>
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
