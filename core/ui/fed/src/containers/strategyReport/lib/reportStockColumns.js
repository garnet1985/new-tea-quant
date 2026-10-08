import React from 'react';
import { Link } from '@mui/material';

export const STOCK_NAME_COLUMN = {
  field: 'stockName',
  headerName: '名称',
  flex: 1,
  minWidth: 120,
};

export function stockCodeColumn({ onStockSelect, stockLinkEnabled } = {}) {
  return {
    field: 'stockCode',
    headerName: '代码',
    flex: 1,
    minWidth: 120,
    renderCell: (params) => {
      const code = params.value;
      if (!stockLinkEnabled || typeof onStockSelect !== 'function') {
        return code;
      }
      return (
        <Link
          component="button"
          type="button"
          underline="hover"
          onClick={(event) => {
            event.stopPropagation();
            onStockSelect(params.row);
          }}
          sx={{ font: 'inherit', textAlign: 'left' }}
        >
          {code}
        </Link>
      );
    },
  };
}
