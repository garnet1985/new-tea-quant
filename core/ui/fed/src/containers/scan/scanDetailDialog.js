import React from 'react';
import { Button, DataGrid, Dialog } from 'ui';
import {
  OpportunityDetailMeta,
  buildOpportunityColumns,
  formatSessionSummaryLine,
  mapOpportunityRow,
} from './presenterScanReport';
import { readOpportunityCount } from './scanHelpers';

/** 机会明细弹层。 */
export default function ScanDetailDialog({
  open,
  onClose,
  detailPresenterUi,
  detailPayload,
  detailStrategyName,
  detailPresenterHistory,
}) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="机会明细"
      size="lg"
      maxWidth={detailPresenterUi ? 'lg' : 'md'}
      className="scan-detail-dialog"
      actions={<Button variant="glass" onClick={onClose}>关闭</Button>}
    >
      <div className="scan-detail__body">
        {detailPayload ? (
          <>
            <OpportunityDetailMeta
              strategyName={detailStrategyName}
              scanDate={detailPayload?.date || detailPayload?.scan_date}
              opportunityCount={(() => {
                const n = readOpportunityCount(detailPayload);
                if (n != null) return n;
                const ops = detailPayload?.opportunities;
                return Array.isArray(ops) ? ops.length : null;
              })()}
              presenterLine={
                detailPresenterUi && !detailPresenterHistory.error
                  ? (formatSessionSummaryLine(detailPresenterHistory.sessionSummary)
                    || '（无 price 层 overall_report / 尚未回测）')
                  : ''
              }
              presenterError={
                detailPresenterUi ? detailPresenterHistory.error : ''
              }
            />
            <div className="scan-detail__grid">
              <DataGrid
                rows={(() => {
                  const byStock = detailPresenterUi ? detailPresenterHistory.byStock : {};
                  const ops = Array.isArray(detailPayload?.opportunities)
                    ? detailPayload.opportunities
                    : null;
                  if (ops) {
                    return ops.map((o, idx) => mapOpportunityRow(o, idx, byStock));
                  }
                  const list = Array.isArray(detailPayload?.summary?.stocks_with_opportunities)
                    ? detailPayload.summary.stocks_with_opportunities
                    : [];
                  return list.map((code, idx) => mapOpportunityRow(
                    { stock_id: code },
                    idx,
                    byStock,
                  ));
                })()}
                columns={buildOpportunityColumns({ withPresenter: Boolean(detailPresenterUi) })}
                getRowHeight={() => 'auto'}
                pageSizeOptions={[10, 25, 50]}
                initialState={{
                  pagination: { paginationModel: { page: 0, pageSize: 10 } },
                }}
              />
            </div>
          </>
        ) : (
          <p className="ntq-muted">暂无明细。</p>
        )}
      </div>
    </Dialog>
  );
}
