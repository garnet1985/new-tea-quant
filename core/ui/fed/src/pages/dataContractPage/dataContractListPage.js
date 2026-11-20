import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  DataGrid,
  ListToolbar,
  Message,
  SearchField,
  Section,
  Tag,
} from 'ui';
import { showToast } from 'ui/message/toast';
import { PageLayout } from 'ntq-ui';
import {
  fetchDataContractList,
  getDataContractDisplayLabel,
  getDataContractOriginLabel,
  reloadDataContractCatalog,
} from '../../api/dataContractApi';
import './dataContractListPage.scss';

/** 约定：满足 → solid；未满足 → outline */
function BoolTag({ value, trueLabel, falseLabel }) {
  return value ? (
    <Tag status="success" variant="solid">{trueLabel}</Tag>
  ) : (
    <Tag status="neutral" variant="outline">{falseLabel}</Tag>
  );
}

function DataContractListPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rediscovering, setRediscovering] = useState(false);
  const [pageReady, setPageReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const key = String(r.key || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
      return key.includes(q) || label.includes(q);
    });
  }, [rows, nameQuery]);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchDataContractList({ page: 1, limit: 500 })
      .then((res) => {
        setRows(Array.isArray(res?.data) ? res.data : []);
      })
      .catch((e) => {
        setRows([]);
        setLoadError(e?.message || '加载数据契约列表失败');
      })
      .finally(() => {
        setLoading(false);
        setPageReady(true);
      });
  }, []);

  const rediscover = useCallback(() => {
    setRediscovering(true);
    setLoading(true);
    setLoadError('');
    reloadDataContractCatalog({ page: 1, limit: 500 })
      .then((res) => {
        setRows(Array.isArray(res?.data) ? res.data : []);
        const total = Number(res?.total) || 0;
        showToast({
          status: 'success',
          content: `已重新发现 ${total} 个数据契约（无需重启 NTQ）`,
        });
      })
      .catch((e) => {
        setLoadError(e?.message || '重新发现数据契约失败');
      })
      .finally(() => {
        setRediscovering(false);
        setLoading(false);
        setPageReady(true);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPaginationModel((m) => ({ ...m, page: 0 }));
  }, [nameQuery]);

  const columns = useMemo(() => ([
    {
      field: 'display_name',
      headerName: '名称',
      minWidth: 180,
      flex: 0.45,
      valueGetter: (params) => getDataContractDisplayLabel(params.row),
      renderCell: (params) => (
        <span className="data-contract-list-cell-name">
          {params.value || params.row.key}
        </span>
      ),
    },
    {
      field: 'key',
      headerName: 'Key',
      minWidth: 220,
      flex: 0.55,
      renderCell: (params) => (
        <span
          className="data-contract-list-key ntq-muted"
          data-ntq-help="data-contract-list-key"
        >
          {params.value}
        </span>
      ),
    },
    {
      field: 'origin',
      headerName: '来源',
      width: 100,
      valueGetter: (params) => getDataContractOriginLabel(params.row.origin),
      renderCell: (params) => (
        <span data-ntq-help="data-contract-list-origin">
          {params.row.is_custom ? (
            <Tag status="info" variant="outline">{params.value}</Tag>
          ) : (
            <Tag status="neutral" variant="outline">{params.value}</Tag>
          )}
        </span>
      ),
    },
    {
      field: 'is_time_series',
      headerName: '时序',
      width: 100,
      renderCell: (params) => (
        <span data-ntq-help="data-contract-list-time-series">
          <BoolTag value={Boolean(params.value)} trueLabel="是" falseLabel="否" />
        </span>
      ),
    },
    {
      field: 'is_per_entity',
      headerName: '按实体',
      width: 100,
      renderCell: (params) => (
        <span data-ntq-help="data-contract-list-per-entity">
          <BoolTag value={Boolean(params.value)} trueLabel="是" falseLabel="否" />
        </span>
      ),
    },
  ]), []);

  const busy = loading || rediscovering;

  return (
    <PageLayout
      className="data-contract-list-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="数据契约"
      bannerTitle="数据契约"
      bannerDescription="系统与用户扩展合并后的数据契约目录，供策略与特征标签引用数据键。"
      loading={!pageReady}
      loadingMessage="正在加载数据契约…"
    >
      <Section className="data-contract-list-page__stack" gap="md">
        {loadError ? <Message status="error">{loadError}</Message> : null}

        <Section className="data-contract-list-grid" gap="md">
          <ListToolbar
            search={(
              <SearchField
                fluid
                surface="glass"
                placeholder="搜索名称或 Key"
                label="搜索数据契约"
                value={nameQuery}
                onChange={(e) => setNameQuery(e.target.value)}
              />
            )}
            actions={(
              <span data-ntq-help="data-contract-list-rediscover">
                <Button
                  variant="glass"
                  icon="refresh"
                  onClick={rediscover}
                  disabled={busy}
                >
                  {rediscovering ? '发现中…' : '重新发现'}
                </Button>
              </span>
            )}
          />

          <div className="data-contract-list-grid-body">
            <DataGrid
              autoHeight
              rows={displayRows}
              columns={columns}
              loading={busy}
              pageSizeOptions={[10, 25, 50, 100]}
              paginationModel={paginationModel}
              onPaginationModelChange={setPaginationModel}
              getRowId={(row) => row.id}
            />
          </div>
        </Section>
      </Section>
    </PageLayout>
  );
}

export default DataContractListPage;
