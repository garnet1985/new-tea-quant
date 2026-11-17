import React, { useMemo, useState } from 'react';
import DataGrid from 'ui/table/dataGrid';
import Tag from 'ui/tag/tag';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

const DEMO_ROWS = [
  { id: 1, name: '沪深 300', code: '000300', status: 'enabled', updated: '2026-04-10' },
  { id: 2, name: '中证 500', code: '000905', status: 'enabled', updated: '2026-04-09' },
  { id: 3, name: '创业板指', code: '399006', status: 'disabled', updated: '2026-03-28' },
  { id: 4, name: '科创 50', code: '000688', status: 'pending', updated: '2026-04-08' },
];

function statusTag(status) {
  if (status === 'enabled') return <Tag status="success">已启用</Tag>;
  if (status === 'pending') return <Tag status="warning">待更新</Tag>;
  return <Tag status="neutral">已禁用</Tag>;
}

function DataGridShowcase() {
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 5 });
  const [loading, setLoading] = useState(false);

  const columns = useMemo(() => [
    { field: 'name', headerName: '名称', flex: 1, minWidth: 120 },
    { field: 'code', headerName: '代码', width: 100 },
    {
      field: 'status',
      headerName: '状态',
      width: 110,
      sortable: false,
      renderCell: (params) => statusTag(params.value),
    },
    { field: 'updated', headerName: '更新', width: 120 },
  ], []);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="基础列表（autoHeight + 分页）" block>
          <DataGrid
            autoHeight
            rows={DEMO_ROWS}
            columns={columns}
            pageSizeOptions={[5, 10]}
            paginationModel={paginationModel}
            onPaginationModelChange={setPaginationModel}
          />
        </SampleRow>
        <SampleRow label="加载态（loading）" block>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <label className="ntq-caption" style={{ display: 'inline-flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={loading}
                onChange={(e) => setLoading(e.target.checked)}
              />
              模拟 loading
            </label>
            <DataGrid
              autoHeight
              loading={loading}
              rows={DEMO_ROWS}
              columns={columns}
              hideFooter
            />
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='density="sm" / "md"' block>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <p className="ntq-caption" style={{ margin: 0 }}>sm · 紧凑</p>
            <DataGrid
              density="sm"
              autoHeight
              rows={DEMO_ROWS.slice(0, 2)}
              columns={columns}
              hideFooter
            />
            <p className="ntq-caption" style={{ margin: 0 }}>md · 标准（默认）</p>
            <DataGrid
              density="md"
              autoHeight
              rows={DEMO_ROWS.slice(0, 2)}
              columns={columns}
              hideFooter
            />
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          单元格 padding 随
          {' '}
          <Text variant="code">density</Text>
          ；与外层区块间距交给父级
          {' '}
          <Text variant="code">gap</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          表头 / 分隔线走 token（
          <Text variant="code">--ntq-white-*</Text>
          ）；状态色在单元格内用
          {' '}
          <Text variant="code">Tag</Text>
          等组件表达。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          默认无外边框；覆盖层玻璃底；列定义与
          {' '}
          <Text variant="code">renderCell</Text>
          由业务传入。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const showcases = {
  dataGrid: DataGridShowcase,
};

export default showcases;
