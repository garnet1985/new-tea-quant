import React from 'react';

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
        <button
          type="button"
          className="ntq-link"
          onClick={(event) => {
            event.stopPropagation();
            onStockSelect(params.row);
          }}
        >
          {code}
        </button>
      );
    },
  };
}
