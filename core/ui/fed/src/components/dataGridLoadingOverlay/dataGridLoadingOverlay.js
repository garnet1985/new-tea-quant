import React from 'react';
import { GridOverlay } from '@mui/x-data-grid';
import InlineLoadingState from '../inlineLoadingState/inlineLoadingState';

export function DataGridLoadingOverlay() {
  return (
    <GridOverlay>
      <InlineLoadingState compact />
    </GridOverlay>
  );
}

/** 挂到 MUI DataGrid ``slots``，统一竖条 loading 覆盖层。 */
export const NTQ_DATA_GRID_LOADING_SLOTS = {
  loadingOverlay: DataGridLoadingOverlay,
};
