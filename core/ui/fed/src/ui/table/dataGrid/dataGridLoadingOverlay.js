import React from 'react';
import { GridOverlay } from '@mui/x-data-grid';
import Loading from 'ui/progress/loading';

/** DataGrid 加载覆盖层：统一竖条 Loading。 */
export function DataGridLoadingOverlay() {
  return (
    <GridOverlay>
      <Loading variant="inline" aria-label="表格加载中" />
    </GridOverlay>
  );
}

/** 默认 slots；可与业务自定义 slots 合并。 */
export const NTQ_DATA_GRID_LOADING_SLOTS = {
  loadingOverlay: DataGridLoadingOverlay,
};
