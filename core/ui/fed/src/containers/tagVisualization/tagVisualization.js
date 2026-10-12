import React, { useEffect, useMemo, useState } from 'react';
import {
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import ReactECharts from 'echarts-for-react';
import { fetchTagVisualization } from 'api/tagApi';
import NtqIcon from 'views/ntqIcon';
import NtqButton from 'views/ntqButton';
import Message from 'views/message';
import InlineLoadingState from 'views/inlineLoadingState';
import SearchField from 'views/searchField';
import { NTQ_DATA_GRID_LOADING_SLOTS } from 'views/dataGridLoadingOverlay';
import {
  buildTagGanttOption,
  countEntitiesByValue,
  formatVizDate,
  snapshotBoardCards,
  tagValueColor,
} from './tagVisualization.service';
import './style.scss';

const GRID_LOCALE = zhCN.components.MuiDataGrid.defaultProps.localeText;

const ENTITY_COLUMNS = [
  {
    field: 'entity',
    headerName: '实体',
    flex: 1,
    minWidth: 180,
    valueGetter: (params) => {
      const name = params.row.entity_name || '';
      const code = params.row.entity_id || '';
      return name && code && name !== code ? `${name} ${code}` : (name || code);
    },
    renderCell: (params) => {
      const name = params.row.entity_name || '';
      const code = params.row.entity_id || '';
      if (!code || name === code) {
        return <Typography variant="body2" noWrap>{name || code}</Typography>;
      }
      return (
        <span className="tag-viz-dialog__heading">
          <Typography variant="body2" noWrap>{name}</Typography>
          <Typography variant="caption" color="text.secondary" noWrap>{code}</Typography>
        </span>
      );
    },
  },
  {
    field: 'tag_label',
    headerName: '当前标签',
    flex: 0.8,
    minWidth: 140,
    valueGetter: (params) => params.row.tag_label || params.row.value_label || '',
    renderCell: (params) => {
      const tag = params.row.tag_label || params.row.value_label || '';
      const detail = params.row.value_detail || '';
      if (!detail || detail === tag) {
        return <Typography variant="body2" noWrap>{tag}</Typography>;
      }
      return (
        <span className="tag-viz-dialog__heading">
          <Typography variant="body2" noWrap>{tag}</Typography>
          <Typography variant="caption" color="text.secondary" noWrap>{detail}</Typography>
        </span>
      );
    },
  },
  {
    field: 'as_of',
    headerName: '最近变化日',
    width: 130,
    valueFormatter: (params) => formatVizDate(params.value) || '—',
  },
];

const CATEGORY_COLUMNS = [
  { field: 'name', headerName: '类别', flex: 0.6, minWidth: 120 },
  {
    field: 'count',
    headerName: '数量',
    width: 90,
    valueFormatter: (params) => (params.value == null ? '—' : params.value),
  },
  { field: 'detail', headerName: '说明', flex: 1, minWidth: 160 },
  { field: 'samples', headerName: '样例', flex: 0.8, minWidth: 140 },
];

const FIELD_COLUMNS = [
  { field: 'name', headerName: '字段', flex: 0.6, minWidth: 140 },
  { field: 'value', headerName: '值', flex: 1, minWidth: 180 },
];

function routeNote(route, drilled) {
  if (route === 'non_time_series') return '当前快照，没有时间轴。';
  if (route === 'per_entity' && !drilled) return '点一行查看该实体各标签随时间的变化。';
  return '纵轴是标签，横轴是时间。悬停可以看到取值。一段接到下一次变化，最后一段收到计算水位。';
}

function routeSubtitle(route, drilledLabel) {
  if (route === 'global') return '时序 · 全局';
  if (route === 'non_time_series') return '非时序';
  if (route === 'per_entity') return drilledLabel ? `时序 · ${drilledLabel}` : '时序 · 按实体';
  return '';
}

function shareLabel(count, total) {
  if (!total) return '0%';
  const pct = (count / total) * 100;
  return pct >= 10 ? `${Math.round(pct)}%` : `${pct.toFixed(1)}%`;
}

function SnapshotBoard({ board }) {
  return (
    <div className="tag-viz-dialog__board">
      <div className="tag-viz-dialog__board-meta">
        <span className="tag-viz-dialog__board-total">{board.total}</span>
        <span>只</span>
        {board.asOf ? <span>截至 {formatVizDate(board.asOf)}</span> : null}
      </div>
      <div className="tag-viz-dialog__share">
        {board.cards.map((card) => (
          <div
            key={card.key || card.name}
            className="tag-viz-dialog__share-seg"
            style={{ flexGrow: Math.max(card.count, 0.35), '--tag-accent': tagValueColor(card.name) }}
            title={`${card.name} ${card.count}只`}
          >
            <span>{card.name}</span>
          </div>
        ))}
      </div>
      <div className="tag-viz-dialog__cards">
        {board.cards.map((card) => (
          <article
            key={card.key || card.name}
            className="tag-viz-dialog__card"
            style={{ '--tag-accent': tagValueColor(card.name) }}
          >
            <header className="tag-viz-dialog__card-head">
              <span className="tag-viz-dialog__card-name">{card.name}</span>
              <span className="tag-viz-dialog__card-share">{shareLabel(card.count, board.total)}</span>
            </header>
            <div className="tag-viz-dialog__card-count">
              {card.count}
              <span>只</span>
            </div>
            {card.provinces.length ? (
              <div className="tag-viz-dialog__pills">
                {card.provinces.map((name) => (
                  <span key={name} className="tag-viz-dialog__pill">{name}</span>
                ))}
              </div>
            ) : null}
            {card.samples.length ? (
              <p className="tag-viz-dialog__samples">
                <span>样例</span>
                {card.samples.join('  ')}
              </p>
            ) : null}
            {card.unmapped ? (
              <p className="tag-viz-dialog__unmapped">未映射 {card.unmapped}</p>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

function SnapshotBlock({ snapshot }) {
  if (!snapshot) return null;
  if (snapshot.kind === 'scalar') {
    return (
      <div className="tag-viz-dialog__scalar">
        <Typography variant="h5">{snapshot.scalar || '—'}</Typography>
        {snapshot.as_of ? (
          <Typography variant="caption" color="text.secondary">
            {formatVizDate(snapshot.as_of)}
          </Typography>
        ) : null}
      </div>
    );
  }
  if (snapshot.kind === 'categories') {
    const rows = (snapshot.categories || []).map((row, index) => ({
      id: `${row.name}-${index}`,
      ...row,
    }));
    return (
      <div className="tag-viz-dialog__grid">
        <DataGrid
          rows={rows}
          columns={CATEGORY_COLUMNS}
          disableRowSelectionOnClick
          pageSizeOptions={[10, 25]}
          initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
          localeText={GRID_LOCALE}
          slots={NTQ_DATA_GRID_LOADING_SLOTS}
        />
      </div>
    );
  }
  if (snapshot.kind === 'fields') {
    const rows = (snapshot.fields || []).map((row, index) => ({
      id: `${row.name}-${index}`,
      ...row,
    }));
    return (
      <div className="tag-viz-dialog__grid">
        <DataGrid
          rows={rows}
          columns={FIELD_COLUMNS}
          disableRowSelectionOnClick
          hideFooter
          localeText={GRID_LOCALE}
          slots={NTQ_DATA_GRID_LOADING_SLOTS}
        />
      </div>
    );
  }
  return <pre className="tag-viz-dialog__pre">{snapshot.text || '—'}</pre>;
}

function TagVisualization({ open, tagKey, displayName, onClose }) {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedEntityId, setSelectedEntityId] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (open) return undefined;
    setSelectedEntityId('');
    setSelectedLabel('');
    setPayload(null);
    setError('');
    setQuery('');
    return undefined;
  }, [open]);

  useEffect(() => {
    if (!open || !tagKey) return undefined;
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchTagVisualization(tagKey, selectedEntityId)
      .then((data) => {
        if (!cancelled) setPayload(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setPayload(null);
          setError(err?.message || '读取可视化数据失败');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, tagKey, selectedEntityId]);

  const route = payload?.route || '';
  const drilled = Boolean(selectedEntityId);
  const showEntityTable = route === 'per_entity' && !drilled;
  const showSnapshots = route === 'non_time_series';
  const intervals = useMemo(() => payload?.intervals || [], [payload]);
  const lanes = useMemo(() => payload?.lanes || [], [payload]);
  const chartOption = useMemo(
    () => (showEntityTable || showSnapshots ? null : buildTagGanttOption(intervals, lanes)),
    [intervals, lanes, showEntityTable, showSnapshots],
  );
  const entities = useMemo(() => payload?.entities || [], [payload]);
  const distribution = useMemo(() => countEntitiesByValue(entities), [entities]);
  const filteredEntities = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return entities;
    return entities.filter((row) => {
      const name = String(row.entity_name || '').toLowerCase();
      const code = String(row.entity_id || '').toLowerCase();
      const value = String(row.tag_label || row.value_label || '').toLowerCase();
      const detail = String(row.value_detail || '').toLowerCase();
      return name.includes(q) || code.includes(q) || value.includes(q) || detail.includes(q);
    });
  }, [entities, query]);

  const snapshotBoard = useMemo(
    () => (showSnapshots ? snapshotBoardCards(payload?.snapshots) : null),
    [payload, showSnapshots],
  );
  const title = payload?.display_name || displayName || tagKey;
  const chartHeight = chartOption?.yAxis?.data
    ? Math.min(560, Math.max(320, chartOption.yAxis.data.length * 44 + 96))
    : 360;

  const handleClose = () => {
    if (onClose) onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullWidth
      maxWidth="lg"
      className="tag-viz-dialog"
    >
      <DialogTitle className="tag-viz-dialog__title">
        <span className="tag-viz-dialog__heading">
          <Typography variant="subtitle1" fontWeight={700} component="span">
            {title || '标签可视化'}
          </Typography>
          {route ? (
            <Typography component="span" variant="caption" color="text.secondary">
              {routeSubtitle(route, drilled ? selectedLabel : '')}
            </Typography>
          ) : null}
        </span>
        <IconButton aria-label="关闭" onClick={handleClose} edge="end">
          <NtqIcon name="cancel" size={18} />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers className="tag-viz-dialog__body">
        {drilled ? (
          <div>
            <NtqButton
              variant="ghost"
              className="tag-viz-dialog__back"
              icon="arrowBack"
              iconSize={18}
              onClick={() => {
                setSelectedEntityId('');
                setSelectedLabel('');
              }}
            >
              返回实体列表
            </NtqButton>
          </div>
        ) : null}
        {error ? <Message severity="error">{error}</Message> : null}
        {loading ? <InlineLoadingState message="正在加载标签数据…" /> : null}
        {!loading && !error && payload ? (
          <>
            <Typography variant="caption" color="text.secondary" className="tag-viz-dialog__note">
              {routeNote(route, drilled)}
            </Typography>
            {showEntityTable && !entities.length ? (
              <Typography variant="body2" color="text.secondary">暂无实体标签值。</Typography>
            ) : null}
            {showEntityTable && entities.length ? (
              <>
                {distribution.length ? (
                  <div className="tag-viz-dialog__distribution">
                    {distribution.map((item) => (
                      <Chip
                        key={item.label}
                        size="small"
                        variant="outlined"
                        label={`${item.label} ${item.count}`}
                        style={{
                          borderColor: tagValueColor(item.label),
                          color: tagValueColor(item.label),
                        }}
                      />
                    ))}
                  </div>
                ) : null}
                <SearchField
                  fluid
                  placeholder="搜索代码、名称或取值"
                  label="搜索实体"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
                <div className="tag-viz-dialog__grid tag-viz-dialog__grid--entities">
                  <DataGrid
                    rows={filteredEntities}
                    columns={ENTITY_COLUMNS}
                    getRowId={(row) => row.entity_id}
                    disableRowSelectionOnClick
                    onRowClick={(params) => {
                      const name = params.row.entity_name || '';
                      const code = params.row.entity_id || '';
                      setSelectedLabel(name && name !== code ? `${name} ${code}` : code);
                      setSelectedEntityId(code);
                    }}
                    pageSizeOptions={[10, 25, 50]}
                    initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
                    localeText={GRID_LOCALE}
                    slots={NTQ_DATA_GRID_LOADING_SLOTS}
                  />
                </div>
              </>
            ) : null}
            {showSnapshots && snapshotBoard ? <SnapshotBoard board={snapshotBoard} /> : null}
            {showSnapshots && !snapshotBoard ? (
              (payload.snapshots || []).length ? (
                payload.snapshots.map((snapshot) => (
                  <section key={snapshot.tag_name || snapshot.tag_display_name} className="tag-viz-dialog__section">
                    {(payload.snapshots.length > 1) ? (
                      <Typography variant="subtitle2">
                        {snapshot.tag_display_name || snapshot.tag_name}
                      </Typography>
                    ) : null}
                    <SnapshotBlock snapshot={snapshot} />
                  </section>
                ))
              ) : (
                <Typography variant="body2" color="text.secondary">暂无标签值。</Typography>
              )
            ) : null}
            {!showEntityTable && !showSnapshots ? (
              chartOption ? (
                <div className="tag-viz-dialog__chart">
                  <ReactECharts
                    option={chartOption}
                    style={{ height: chartHeight, width: '100%' }}
                    notMerge
                    lazyUpdate
                  />
                </div>
              ) : (
                <Typography variant="body2" color="text.secondary">暂无区间数据。</Typography>
              )
            ) : null}
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

export default TagVisualization;
