import React from 'react';
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
  gridHeight = 360,
}) {
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
        </Stack>
        <Box sx={{ height: gridHeight }}>
          <DataGrid
            rows={rows}
            columns={columns}
            hideFooter
            disableColumnMenu
            disableColumnFilter
            disableRowSelectionOnClick
            density="compact"
          />
        </Box>
      </Stack>
    </SectionBlock>
  );
}

export default ReportStockSampleGrid;
