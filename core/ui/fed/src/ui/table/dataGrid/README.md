# dataGrid

NTQ 表格（MUI DataGrid 封装）。

```js
import DataGrid from 'ui/table/dataGrid';

<DataGrid
  autoHeight
  rows={rows}
  columns={columns}
  loading={loading}
  pageSizeOptions={[10, 25, 50]}
  paginationModel={paginationModel}
  onPaginationModelChange={setPaginationModel}
/>
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `density` | `sm` `md` | `md` |
| `loading` | boolean | `false` |
| `autoHeight` | boolean | `false` |
| 其余 | MUI DataGrid props | 中文 locale + Loading overlay |

另导出：`NTQ_DATA_GRID_LOADING_SLOTS`、`DataGridLoadingOverlay`、`LOCALE_TEXT`。
