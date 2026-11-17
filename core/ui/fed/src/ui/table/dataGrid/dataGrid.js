import React, { useMemo } from 'react';
import { DataGrid as MuiDataGrid, GridRow } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import {
  DATA_GRID_CELL_LAYOUT_TOKENS,
  DATA_GRID_DENSITY_TOKENS,
  pickToken,
} from 'ui/tokens';
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
 * - 默认中文 locale、Loading 覆盖层、描边边框、禁用点击选行
 * - density：sm（紧凑）/ md（标准）
 * - cellLayout：center（单行垂直居中）/ wrap（多行换行顶齐）
 * - bordered：默认 true；嵌在已有描边容器内时可传 false
 * - 其余 props 透传给 MUI DataGrid（业务应优先用 density / cellLayout，少用 sx）
 *
 * @example
 * <DataGrid rows={rows} columns={columns} loading={loading} autoHeight />
 * <DataGrid density="sm" bordered={false} rows={…} columns={…} />
 * <DataGrid cellLayout="wrap" getRowHeight={() => 'auto'} rows={…} columns={…} />
 */
function DataGrid({
  density = 'md',
  cellLayout = 'center',
  bordered = true,
  className = '',
  slots,
  slotProps,
  localeText,
  disableRowSelectionOnClick = true,
  sx,
  ...rest
}) {
  const densityToken = pickToken(density, DATA_GRID_DENSITY_TOKENS, 'md');
  const cellLayoutToken = pickToken(cellLayout, DATA_GRID_CELL_LAYOUT_TOKENS, 'center');

  const mergedSlots = useMemo(() => ({
    ...NTQ_DATA_GRID_LOADING_SLOTS,
    ...slots,
  }), [slots]);

  const rootClass = [
    'ntq-data-grid',
    `ntq-data-grid--${densityToken}`,
    `ntq-data-grid--cell-${cellLayoutToken}`,
    bordered ? 'ntq-data-grid--bordered' : 'ntq-data-grid--borderless',
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
      sx={sx}
    />
  );
}

export default DataGrid;
export {
  DataGridLoadingOverlay,
  NTQ_DATA_GRID_LOADING_SLOTS,
  LOCALE_TEXT,
  /** 自定义行渲染时用（如行内进度条），避免业务直连 @mui/x-data-grid */
  GridRow,
};
