import React from 'react';
import {
  Button,
  CategoryChipStrip,
  CountBadge,
  DataGrid,
  ListToolbar,
  Loading,
  Message,
  ProgressBar,
  SearchField,
  Section,
} from 'ui';
import DataEndTruncationAlert from 'containers/dataEndTruncation';

/** 策略搜索 / 归类 / 表格列表。 */
export default function ScanStrategyListSection({
  nameQuery,
  onNameQueryChange,
  running,
  loading,
  onRefresh,
  catalogGroups,
  rows,
  categoryQuery,
  setCategoryQuery,
  toggleCategoryQuery,
  selectedChipRef,
  loadError,
  readinessError,
  onClearReadinessError,
  dataEnd,
  readinessLoading,
  mode,
  strictBlockReason,
  runError,
  progress,
  catalogHasSelectedCategory,
  groupedRows,
  columns,
}) {
  return (
    <Section className="scan-section scan-section--list" gap="md">
      <ListToolbar
        search={(
          <SearchField
            fluid
            surface="glass"
            placeholder="输入策略名称搜索"
            label="按策略名搜索"
            value={nameQuery}
            onChange={onNameQueryChange}
          />
        )}
        actions={(
          <Button
            variant="glass"
            icon="refresh"
            disabled={running || loading}
            onClick={onRefresh}
          >
            刷新策略列表
          </Button>
        )}
        hint="一次仅允许扫描一个策略；运行中会禁用其它策略的扫描按钮。"
      />

      {catalogGroups.length > 0 ? (
        <CategoryChipStrip
          all={{
            label: '全部',
            count: rows.length,
            selected: !categoryQuery,
            onClick: () => setCategoryQuery(''),
          }}
          items={catalogGroups.map(({ category, queryValue, rows: categoryRows }) => ({
            key: queryValue,
            label: category,
            count: categoryRows.length,
            title: category,
            selected: categoryQuery === queryValue,
            onClick: () => toggleCategoryQuery(queryValue),
          }))}
          selectedItemRef={selectedChipRef}
        />
      ) : null}

      {loadError ? <Message status="error">{loadError}</Message> : null}
      {readinessError ? (
        <Message status="warning" onClose={onClearReadinessError}>
          {readinessError}
        </Message>
      ) : null}
      <DataEndTruncationAlert dataEnd={dataEnd} />
      {!readinessLoading && mode === 'strict' && strictBlockReason ? (
        <Message status="warning">{strictBlockReason}</Message>
      ) : null}
      {runError && runError !== strictBlockReason ? (
        <Message status="error">{runError}</Message>
      ) : null}

      {running ? (
        <ProgressBar
          className="scan-progress"
          size="md"
          value={progress.pct}
          label={progress.label}
          showPercent
        />
      ) : null}

      <div className={[
        'scan-strategy-list',
        loading && rows.length === 0 ? 'scan-strategy-list--loading' : '',
      ].filter(Boolean).join(' ')}
      >
        {loading && rows.length === 0 ? (
          <Loading variant="inline" message="正在加载策略列表…" />
        ) : !loading && categoryQuery && !catalogHasSelectedCategory ? (
          <p className="ntq-muted scan-category-empty">没有该归类的策略</p>
        ) : groupedRows.length === 0 ? (
          <p className="ntq-muted scan-category-empty">
            {nameQuery.trim() ? '没有匹配的策略' : '暂无策略'}
          </p>
        ) : (
          <div className="scan-category-stack">
            {groupedRows.map(({ category, queryValue, rows: categoryRows }, index) => (
              <div
                key={queryValue}
                className="scan-category-section"
                data-ntq-help={index === 0 ? 'scan-strategy-list' : undefined}
              >
                <div className="scan-category">
                  <button
                    type="button"
                    className="scan-category-header-btn"
                    onClick={() => toggleCategoryQuery(queryValue)}
                    aria-pressed={categoryQuery === queryValue}
                    title={categoryQuery === queryValue ? '显示全部归类' : `只看${category}`}
                  >
                    <span className="scan-category-header-label">{category}</span>
                    <CountBadge
                      count={categoryRows.length}
                      label={`${categoryRows.length} 个策略`}
                    />
                  </button>
                </div>
                <DataGrid
                  autoHeight
                  rows={categoryRows}
                  columns={columns}
                  loading={false}
                  getRowHeight={() => 'auto'}
                  hideFooter
                  className="scan-strategy-grid"
                  cellLayout="wrap"
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}
