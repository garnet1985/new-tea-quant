import React, { useMemo } from 'react';
import { DataGrid as MuiDataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import { DATA_GRID_DENSITY_TOKENS, pickToken } from 'ui/tokens';
import {
  DataGridLoadingOverlay,
  NTQ_DATA_GRID_LOADING_SLOTS,
} from './dataGridLoadingOverlay';
import './style.scss';

const LOCALE_TEXT = zhCN.components.MuiDataGrid.defaultProps.localeText;

const DENSITY_TO_MUI = {
  sm: 'compact',
  md: 'standard',
};

/**
 * NTQ 表格（MUI DataGrid 封装）。
 * - 默认中文 locale、Loading 覆盖层、无边框、禁用点击选行
 * - density：sm（紧凑）/ md（标准）
 * - 其余 props 透传给 MUI DataGrid
 *
 * @example
 * <DataGrid rows={rows} columns={columns} loading={loading} autoHeight />
 * <DataGrid density="sm" rows={…} columns={…} />
 */
function DataGrid({
  density = 'md',
  className = '',
  slots,
  slotProps,
  localeText,
  disableRowSelectionOnClick = true,
  sx,
  ...rest
}) {
  const densityToken = pickToken(density, DATA_GRID_DENSITY_TOKENS, 'md');

  const mergedSlots = useMemo(() => ({
    ...NTQ_DATA_GRID_LOADING_SLOTS,
    ...slots,
  }), [slots]);

  const rootClass = [
    'ntq-data-grid',
    `ntq-data-grid--${densityToken}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <MuiDataGrid
      {...rest}
      className={rootClass}
      density={DENSITY_TO_MUI[densityToken]}
      disableRowSelectionOnClick={disableRowSelectionOnClick}
      localeText={localeText || LOCALE_TEXT}
      slots={mergedSlots}
      slotProps={slotProps}
      sx={{
        border: 'none',
        ...(sx || {}),
      }}
    />
  );
}

export default DataGrid;
export { DataGridLoadingOverlay, NTQ_DATA_GRID_LOADING_SLOTS, LOCALE_TEXT };
