import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { DataGrid, Select, TextField } from 'ui';
import { SectionBlock } from 'views/sectionBlock';
import './style.scss';

/**
 * 搜索 + 排序 + DataGrid（行数据与列定义由调用方传入）
 */
function ReportStockSampleGrid({
  title,
  tip,
  headerAction,
  searchValue,
  onSearchChange,
  searchPlaceholder = '搜索代码或名称...',
  sortValue,
  onSortChange,
  sortSelectLabelId = 'report-stock-sort-label',
  sortLabel = '排序',
  sortMenuItems,
  rows,
  columns,
  gridHeight = 400,
  sortingMode = 'client',
  sortModel,
  onSortModelChange,
  /** 仅 ``sortingMode === 'client'`` 时生效：首屏默认排序（与受控 ``sortModel`` 二选一由调用方约定） */
  initialSortModel,
  pagination = true,
  defaultPageSize = 10,
  pageSizeOptions = [10, 25, 50, 100],
}) {
  const showSortSelect = Array.isArray(sortMenuItems)
    && sortMenuItems.length > 0
    && typeof onSortChange === 'function';

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: defaultPageSize,
  });

  const mountedRef = useRef(false);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const safeSetPaginationModel = useCallback((updater) => {
    if (!mountedRef.current) return;
    setPaginationModel(updater);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const id = requestAnimationFrame(() => {
      if (cancelled || !mountedRef.current) return;
      safeSetPaginationModel((prev) => ({ ...prev, pageSize: defaultPageSize }));
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(id);
    };
  }, [defaultPageSize, safeSetPaginationModel]);

  const rowsFingerprint = useMemo(() => {
    if (!Array.isArray(rows) || rows.length === 0) return '0';
    const last = rows[rows.length - 1];
    return `${rows.length}:${rows[0]?.id}:${last?.id}`;
  }, [rows]);

  useEffect(() => {
    if (!pagination) return;
    let cancelled = false;
    const id = requestAnimationFrame(() => {
      if (cancelled || !mountedRef.current) return;
      safeSetPaginationModel((prev) => ({ ...prev, page: 0 }));
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(id);
    };
  }, [pagination, rowsFingerprint, safeSetPaginationModel]);

  const effectiveGridHeight = Array.isArray(rows) && rows.length > 0
    ? gridHeight
    : Math.min(240, gridHeight);

  const sortOptions = useMemo(
    () => (Array.isArray(sortMenuItems) ? sortMenuItems : []),
    [sortMenuItems],
  );

  return (
    <SectionBlock title={title} tip={tip} action={headerAction}>
      <div className="ntq-report-stock-sample-grid">
        <div className="ntq-report-stock-sample-grid__toolbar">
          <TextField
            className="ntq-report-stock-sample-grid__search"
            labelPlacement="none"
            maxWidth={false}
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
          />
          {showSortSelect ? (
            <Select
              className="ntq-report-stock-sample-grid__sort"
              id={sortSelectLabelId}
              label={sortLabel}
              labelPlacement="none"
              maxWidth={false}
              value={sortValue}
              onChange={(event) => onSortChange(event.target.value)}
              options={sortOptions}
            />
          ) : null}
        </div>
        <div
          className="ntq-report-grid ntq-report-stock-sample-grid__grid"
          style={{ height: effectiveGridHeight }}
        >
          <DataGrid
            rows={rows}
            columns={columns}
            bordered={false}
            density="sm"
            disableColumnMenu
            disableColumnFilter
            sortingOrder={['desc', 'asc']}
            sortingMode={sortingMode}
            sx={{
              width: '100%',
              border: 0,
              '& .MuiDataGrid-virtualScroller': { overflowX: 'auto' },
            }}
            {...(pagination
              ? {
                pagination: true,
                paginationMode: 'client',
                paginationModel,
                onPaginationModelChange: (model) => safeSetPaginationModel(model),
                pageSizeOptions,
              }
              : { pagination: false, hideFooter: true })}
            {...(sortingMode === 'server'
              ? {
                sortModel: Array.isArray(sortModel) ? sortModel : [],
                onSortModelChange,
              }
              : Array.isArray(initialSortModel) && initialSortModel.length > 0
                ? {
                  initialState: {
                    sorting: { sortModel: initialSortModel },
                  },
                }
                : {})}
          />
        </div>
      </div>
    </SectionBlock>
  );
}

export default ReportStockSampleGrid;
