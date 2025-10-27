import React, { useState, useEffect } from 'react';
import { fetchAllOpenTrades, createOperation, createNewTrade, fetchTradeDetail, updateTrade, deleteTrade, updateOperation, deleteOperation } from '../services/investment_api';
import TradeModal from '../components/TradeModal';
import OperationModal from '../components/OperationModal';

function Investment() {
  const [activeTab, setActiveTab] = useState('investing');
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedRow, setExpandedRow] = useState(null);
  const [operationsData, setOperationsData] = useState({}); // { tradeId: [operations] }
  const [modalState, setModalState] = useState({
    showTradeModal: false,
    showOperationModal: false,
    editingTrade: null,
    editingTradeHolding: null,
    editingOperation: null, // 当前编辑的operation
    operationTradeId: null
  });

  useEffect(() => {
    loadTrades();
  }, [activeTab]);

  const loadTrades = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchAllOpenTrades();
      if (response.success) {
        setTrades(response.data || []);
        
        // 加载所有trades的操作记录
        const operationsMap = {};
        for (const trade of response.data || []) {
          try {
            const opsResponse = await fetch(`http://localhost:5001/api/investment/trades/${trade.id}`);
            const opsData = await opsResponse.json();
            if (opsData.success && opsData.data.operations) {
              operationsMap[trade.id] = opsData.data.operations;
            }
          } catch (err) {
            console.error(`加载trade ${trade.id}的操作记录失败:`, err);
          }
        }
        setOperationsData(operationsMap);
      } else {
        setError(response.message || '加载失败');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddOperation = async (tradeId) => {
    setModalState({
      showTradeModal: false,
      showOperationModal: true,
      editingTrade: null,
      operationTradeId: tradeId
    });
  };

  const handleEditTrade = async (tradeId) => {
    const trade = trades.find(t => t.id === tradeId);
    
    // 获取trade详情和持仓信息
    try {
      const response = await fetchTradeDetail(tradeId);
      if (response.success && response.data) {
        setModalState({
          showTradeModal: true,
          showOperationModal: false,
          editingTrade: trade,
          editingTradeHolding: response.data.holding,
          operationTradeId: null
        });
      } else {
        setModalState({
          showTradeModal: true,
          showOperationModal: false,
          editingTrade: trade,
          editingTradeHolding: trade.holding,
          operationTradeId: null
        });
      }
    } catch (err) {
      console.error('获取交易详情失败:', err);
      setModalState({
        showTradeModal: true,
        showOperationModal: false,
        editingTrade: trade,
        editingTradeHolding: trade.holding,
        operationTradeId: null
      });
    }
  };
  
  const handleDeleteTrade = async (tradeId) => {
    const trade = trades.find(t => t.id === tradeId);
    const stockName = trade.stock_name || trade.stock_id;
    
    if (!window.confirm(`确定要删除这笔投资吗？\n股票：${stockName}\n此操作将删除所有相关操作记录，且无法恢复。`)) {
      return;
    }
    
    try {
      await deleteTrade(tradeId);
      await loadTrades();
    } catch (err) {
      setError(err.message || '删除失败');
    }
  };

  const handleCloseModal = () => {
    setModalState({
      showTradeModal: false,
      showOperationModal: false,
      editingTrade: null,
      editingTradeHolding: null,
      editingOperation: null,
      operationTradeId: null
    });
  };

  const handleEditOperation = (tradeId, operation) => {
    setModalState({
      showTradeModal: false,
      showOperationModal: true,
      editingTrade: null,
      editingTradeHolding: null,
      editingOperation: operation,
      operationTradeId: tradeId
    });
  };

  const handleDeleteOperation = async (tradeId, operationId) => {
    const operation = operationsData[tradeId]?.find(op => op.id === operationId);
    const operationDate = operation ? formatDate(operation.date) : '';
    const operationType = operation?.type === 'buy' || operation?.type === 'add' ? '买入' : '卖出';
    
    if (!window.confirm(`确定要删除这个${operationType}操作吗？\n日期：${operationDate}\n删除后持仓将会重新计算。`)) {
      return;
    }
    
    try {
      const response = await deleteOperation(tradeId, operationId);
      if (response.success) {
        await loadTrades();
      } else {
        alert(response.message || '删除失败');
      }
    } catch (err) {
      setError(err.message || '删除失败');
    }
  };

  const handleSaveTrade = async (formData) => {
    try {
      if (modalState.editingTrade) {
        // 更新trade
        const tradeData = {
          strategy: formData.strategy,
          note: formData.note
        };
        await updateTrade(modalState.editingTrade.id, tradeData);
        await loadTrades();
      } else {
        // 创建trade
        const tradeData = {
          stock_id: formData.stock_id,
          strategy: formData.strategy,
          note: formData.note
        };
        const tradeResponse = await createNewTrade(tradeData);
        
        if (tradeResponse.success && formData.first_buy_price && formData.first_buy_amount) {
          // 创建首次买入operation（标记is_first=1）
          const operationData = {
            type: 'buy',
            date: formData.first_buy_date,
            price: parseFloat(formData.first_buy_price),
            amount: parseInt(formData.first_buy_amount),
            note: '首次买入',
            is_first: 1
          };
          await createOperation(tradeResponse.data.id, operationData);
        }
        
        await loadTrades();
      }
      handleCloseModal();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSaveOperation = async (operationData, minDate, maxDate) => {
    try {
      // 标准化日期格式（转换为 YYYY-MM-DD）
      const normalizeDate = (dateStr) => {
        if (!dateStr) return null;
        if (dateStr.includes(',')) {
          return new Date(dateStr).toISOString().split('T')[0];
        }
        return dateStr.split('T')[0].split(' ')[0];
      };
      
      const operationDate = operationData.date;
      const normalizedMinDate = minDate ? normalizeDate(minDate) : null;
      const normalizedMaxDate = maxDate ? normalizeDate(maxDate) : null;
      
      // 验证日期
      if (normalizedMinDate && operationDate < normalizedMinDate) {
        alert(`操作日期不能早于首次买入日期: ${normalizedMinDate}`);
        return;
      }
      if (normalizedMaxDate && operationDate > normalizedMaxDate) {
        alert(`操作日期不能是未来日期`);
        return;
      }
      
      // 判断是新建还是编辑
      if (modalState.editingOperation) {
        // 编辑现有operation
        await updateOperation(modalState.operationTradeId, modalState.editingOperation.id, operationData);
      } else {
        // 新建operation
        await createOperation(modalState.operationTradeId, operationData);
      }
      
      await loadTrades();
      handleCloseModal();
    } catch (err) {
      setError(err.message);
    }
  };

  const toggleRow = (tradeId) => {
    setExpandedRow(expandedRow === tradeId ? null : tradeId);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    
    // 处理数据库返回的 GMT 格式日期
    let date;
    if (dateStr.includes(',')) {
      // 格式: "Mon, 20 Oct 2025 00:00:00 GMT"
      const dateObj = new Date(dateStr);
      date = dateObj.toISOString().split('T')[0]; // 转换为 YYYY-MM-DD
    } else if (dateStr.includes('T')) {
      // 格式: "2025-10-20T00:00:00"
      date = dateStr.split('T')[0];
    } else {
      // 格式: "2025-10-20"
      date = dateStr.split(' ')[0];
    }
    
    return date;
  };

  const formatPercent = (rate) => {
    return `${(rate * 100).toFixed(2)}%`;
  };

  const formatProfit = (rate, amount) => {
    const profitClass = rate >= 0 ? 'profit-positive' : 'profit-negative';
    return (
      <div>
        <div className={profitClass}>{formatPercent(rate)}</div>
        <div className="profit-amount">¥{amount.toFixed(2)}</div>
      </div>
    );
  };

  return (
    <div className="page page-full-width">
      <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ margin: 0 }}>投资管理</h2>
            {activeTab === 'investing' && (
              <button 
                className="btn" 
                onClick={() => setModalState({
                  showTradeModal: true,
                  showOperationModal: false,
                  editingTrade: null,
                  operationTradeId: null
                })}
              >
                + 创建新投资
              </button>
            )}
          </div>
          
          {/* Tab导航 */}
          <div className="tabs">
            <button 
              className={`tab ${activeTab === 'investing' ? 'active' : ''}`}
              onClick={() => setActiveTab('investing')}
            >
              持仓中 ({trades.length})
            </button>
            <button 
              className={`tab ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => setActiveTab('history')}
            >
              历史记录
            </button>
          </div>

          {error && <div className="error">{error}</div>}

          {loading ? (
            <div className="loading">加载中...</div>
          ) : activeTab === 'investing' ? (
            /* 持仓中表格 */
            trades.length === 0 ? (
              <div className="empty-state">
                <p>暂无持仓</p>
                <button 
                  className="btn" 
                  onClick={() => setModalState({
                    showTradeModal: true,
                    showOperationModal: false,
                    editingTrade: null,
                    operationTradeId: null
                  })}
                >
                  创建新投资
                </button>
              </div>
            ) : (
              <div>
                <div className="table-container">
                  <table className="investment-table">
                  <thead>
                    <tr>
                      <th>股票</th>
                      <th>仓位</th>
                      <th>最近股价</th>
                      <th>盈利</th>
                      <th>下一目标</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map(trade => (
                      <React.Fragment key={trade.id}>
                        <tr>
                          {/* Col1: 股票信息（合并ID和名称） */}
                          <td>
                            <div className="stock-info-wrapper">
                              <div className="stock-info-compact">
                                <div className="stock-id-compact">{trade.stock_id}</div>
                                <div className="stock-name-compact">{trade.stock_name}</div>
                                <div className="stock-meta">
                                  {formatDate(trade.holding.first_buy_date)} @ ¥{trade.holding.first_buy_price}
                                </div>
                                {trade.strategy && (
                                  <div className="stock-strategy">策略: {trade.strategy}</div>
                                )}
                              </div>
                              
                              {/* Tooltip显示股票详细信息 */}
                              <div className="tooltip-content">
                                {trade.stock_details && (
                                  <>
                                    {trade.stock_details.current_price_date && (
                                      <div className="tooltip-row" style={{ fontWeight: 'bold', marginBottom: '5px', borderBottom: '1px solid #eee', paddingBottom: '5px' }}>
                                        <span>数据日期: {formatDate(trade.stock_details.current_price_date)}</span>
                                      </div>
                                    )}
                                    
                                    <div style={{ fontWeight: 'bold', margin: '8px 0 4px' }}>价格信息</div>
                                    {trade.stock_details.open != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">开盘:</span>
                                        <span className="tooltip-value">¥{parseFloat(trade.stock_details.open).toFixed(2)}</span>
                                      </div>
                                    )}
                                    {trade.stock_details.high != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">最高:</span>
                                        <span className="tooltip-value">¥{parseFloat(trade.stock_details.high).toFixed(2)}</span>
                                      </div>
                                    )}
                                    {trade.stock_details.low != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">最低:</span>
                                        <span className="tooltip-value">¥{parseFloat(trade.stock_details.low).toFixed(2)}</span>
                                      </div>
                                    )}
                                    {trade.stock_details.close != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">收盘:</span>
                                        <span className="tooltip-value">¥{parseFloat(trade.stock_details.close).toFixed(2)}</span>
                                      </div>
                                    )}
                                    
                                    <div style={{ fontWeight: 'bold', margin: '8px 0 4px' }}>成交信息</div>
                                    {trade.stock_details.turnover_vol != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">成交量:</span>
                                        <span className="tooltip-value">{(parseFloat(trade.stock_details.turnover_vol) / 10000).toFixed(2)}万手</span>
                                      </div>
                                    )}
                                    {trade.stock_details.turnover_value != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">成交额:</span>
                                        <span className="tooltip-value">{(parseFloat(trade.stock_details.turnover_value) / 10000).toFixed(2)}亿</span>
                                      </div>
                                    )}
                                    {trade.stock_details.turnover_rate != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">换手率:</span>
                                        <span className="tooltip-value">{parseFloat(trade.stock_details.turnover_rate).toFixed(2)}%</span>
                                      </div>
                                    )}
                                    
                                    <div style={{ fontWeight: 'bold', margin: '8px 0 4px' }}>财务指标</div>
                                    {trade.stock_details.pe != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">PE:</span>
                                        <span className="tooltip-value">{parseFloat(trade.stock_details.pe).toFixed(2)}</span>
                                      </div>
                                    )}
                                    {trade.stock_details.pb != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">PB:</span>
                                        <span className="tooltip-value">{parseFloat(trade.stock_details.pb).toFixed(2)}</span>
                                      </div>
                                    )}
                                    {trade.stock_details.market_cap != null && (
                                      <div className="tooltip-row">
                                        <span className="tooltip-label">市值:</span>
                                        <span className="tooltip-value">{(parseFloat(trade.stock_details.market_cap) / 100000000).toFixed(2)}亿</span>
                                      </div>
                                    )}
                                    
                                    {trade.stock_details.industry && (
                                      <>
                                        <div style={{ fontWeight: 'bold', margin: '8px 0 4px' }}>基本信息</div>
                                        <div className="tooltip-row">
                                          <span className="tooltip-label">行业:</span>
                                          <span className="tooltip-value">{trade.stock_details.industry}</span>
                                        </div>
                                      </>
                                    )}
                                  </>
                                )}
                              </div>
                            </div>
                          </td>
                          
                          {/* Col2: 仓位信息 */}
                          <td>
                            <div className="holding-info-compact">
                              <div><strong>{trade.holding.amount}</strong> 股</div>
                              <div>成本: <strong>¥{trade.holding.avg_cost}</strong></div>
                              <div className="text-muted">投入: ¥{trade.holding.total_cost.toFixed(2)}</div>
                            </div>
                          </td>
                          
                          {/* Col3: 当前股价 */}
                          <td>
                            <div className="current-price-compact">
                              <div className="price-value"><strong>¥{trade.current_price.price.toFixed(2)}</strong></div>
                              {trade.current_price.date && (
                                <div className="price-date-small">{formatDate(trade.current_price.date)}</div>
                              )}
                            </div>
                          </td>
                          
                          {/* Col4: 当前盈利 */}
                          <td>
                            <div className="profit-compact">
                              {formatProfit(trade.profit.rate, trade.profit.amount)}
                            </div>
                          </td>
                          
                          {/* Col5: 下一目标 */}
                          <td>
                            <div className="next-target-compact">
                              {trade.next_targets && (trade.next_targets.next_stop_loss || trade.next_targets.next_take_profit) ? (
                                <div className="targets-list-compact">
                                  {trade.next_targets.next_take_profit && (
                                    <div className="target-item-compact take-profit">
                                      <span className="target-label">↑</span>
                                      <span className="target-price">¥{trade.next_targets.next_take_profit.target_price?.toFixed(2)}</span>
                                    </div>
                                  )}
                                  {trade.next_targets.next_stop_loss && (
                                    <div className="target-item-compact stop-loss">
                                      <span className="target-label">↓</span>
                                      <span className="target-price">¥{trade.next_targets.next_stop_loss.target_price?.toFixed(2)}</span>
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <span className="placeholder-small">-</span>
                              )}
                            </div>
                          </td>
                          
                          {/* Col6: 操作链接 */}
                          <td>
                            <div className="action-links">
                              <a 
                                href="#"
                                className="action-link"
                                onClick={(e) => { e.preventDefault(); handleEditTrade(trade.id); }}
                              >
                                修改
                              </a>
                              <a 
                                href="#"
                                className="action-link action-link-delete"
                                onClick={(e) => { e.preventDefault(); handleDeleteTrade(trade.id); }}
                              >
                                删除
                              </a>
                              <a 
                                href="#"
                                className="action-link"
                                onClick={(e) => { e.preventDefault(); handleAddOperation(trade.id); }}
                              >
                                +添加操作
                              </a>
                              <a 
                                href="#"
                                className="action-link"
                                onClick={(e) => { e.preventDefault(); toggleRow(trade.id); }}
                              >
                                {expandedRow === trade.id ? '▼' : '▶'}
                              </a>
                            </div>
                          </td>
                        </tr>
                        
                        {/* 展开的操作记录 */}
                        {expandedRow === trade.id && (
                          <tr className="expanded-row">
                            <td colSpan="6">
                              <div className="operations-history">
                                <h4>操作记录</h4>
                                <div className="operations-list">
                                  {operationsData[trade.id] && operationsData[trade.id].length > 0 ? (
                                    operationsData[trade.id].map((op, idx) => (
                                      <div key={idx} className="operation-item">
                                        <span className={`operation-type ${op.type === 'add' ? 'buy' : op.type}`}>
                                          {op.type === 'buy' || op.type === 'add' ? '买入' : '卖出'}
                                        </span>
                                        <span className="operation-date">{formatDate(op.date)}</span>
                                        <span className="operation-price">¥{op.price}</span>
                                        <span className="operation-amount">{op.amount} 股</span>
                                        {op.note && (
                                          <span className="operation-note">{op.note}</span>
                                        )}
                                        <div className="operation-actions" style={{ marginLeft: 'auto', display: 'flex', gap: '5px' }}>
                                          <button 
                                            className="btn-small"
                                            onClick={() => handleEditOperation(trade.id, op)}
                                            style={{ padding: '2px 8px', fontSize: '12px' }}
                                          >
                                            修改
                                          </button>
                                          {op.is_first !== 1 && (
                                            <button 
                                              className="btn-small"
                                              onClick={() => handleDeleteOperation(trade.id, op.id)}
                                              style={{ padding: '2px 8px', fontSize: '12px', backgroundColor: '#dc3545', color: 'white' }}
                                            >
                                              删除
                                            </button>
                                          )}
                                        </div>
                                      </div>
                                    ))
                                  ) : (
                                    <div className="operation-item" style={{ color: '#999', fontStyle: 'italic' }}>
                                      暂无操作记录
                                    </div>
                                  )}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
              </div>
            )
          ) : (
            /* 历史记录 */
            <div className="history-tab">
              <p>历史记录功能待实现</p>
            </div>
          )}
      </div>
      
      {/* Trade Modal */}
      {modalState.showTradeModal && (
              <TradeModal
                trade={modalState.editingTrade}
                isEdit={!!modalState.editingTrade}
                holding={modalState.editingTradeHolding}
                onClose={handleCloseModal}
                onSave={handleSaveTrade}
              />
      )}
      
      {/* Operation Modal */}
      {modalState.showOperationModal && (() => {
        const trade = trades.find(t => t.id === modalState.operationTradeId);
        const firstBuyDate = trade?.holding?.first_buy_date;
        // 标准化日期格式
        const normalizeDate = (dateStr) => {
          if (!dateStr) return null;
          if (dateStr.includes(',')) {
            return new Date(dateStr).toISOString().split('T')[0];
          }
          return dateStr.split('T')[0].split(' ')[0];
        };
        
        return (
          <OperationModal
            tradeId={modalState.operationTradeId}
            operation={modalState.editingOperation}
            isEdit={!!modalState.editingOperation}
            onClose={handleCloseModal}
            onSave={handleSaveOperation}
            minDate={firstBuyDate}
            maxDate={new Date().toISOString().split('T')[0]}
          />
        );
      })()}
    </div>
  );
}

export default Investment;

