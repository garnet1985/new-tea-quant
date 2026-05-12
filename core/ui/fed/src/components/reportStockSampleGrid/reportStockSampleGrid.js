import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { SectionBlock } from '../sectionBlock/sectionBlock';

/**
 * 搜索 + 排序 + DataGrid（行数据与列定义由调用方传入）
 */
function ReportStockSampleGrid({
  title,
  tip,
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

  return (
    <SectionBlock title={title} tip={tip}>
      <Stack spacing={1}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1}>
          <TextField
            size="small"
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
            sx={{ minWidth: { xs: '100%', md: 220 } }}
          />
          {showSortSelect ? (
            <FormControl size="small" sx={{ minWidth: { xs: '100%', md: 200 } }}>
              <InputLabel id={sortSelectLabelId}>{sortLabel}</InputLabel>
              <Select
                labelId={sortSelectLabelId}
                value={sortValue}
                label={sortLabel}
                onChange={(event) => onSortChange(event.target.value)}
              >
                {sortMenuItems.map((item) => (
                  <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : null}
        </Stack>
        <Box className="ntq-report-grid" sx={{ height: effectiveGridHeight }}>
          <DataGrid
            rows={rows}
            columns={columns}
            disableColumnMenu
            disableColumnFilter
            disableRowSelectionOnClick
            sortingOrder={['desc', 'asc']}
            sortingMode={sortingMode}
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
            density="compact"
          />
        </Box>
      </Stack>
    </SectionBlock>
  );
}

export default ReportStockSampleGrid;
