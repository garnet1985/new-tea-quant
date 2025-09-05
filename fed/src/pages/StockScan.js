import React, { useState } from 'react';
import { fetchStockScan } from '../services/api';

function StockScan() {
  const [stockId, setStockId] = useState('000002.SZ');
  const [strategy, setStrategy] = useState('historicLow');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchStockScan(strategy, stockId);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <h2>策略扫描</h2>
        <p>使用历史低点策略扫描股票，寻找投资机会</p>
        
        <form onSubmit={handleSubmit} style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '1rem', alignItems: 'end' }}>
            <div className="form-group">
              <label htmlFor="stockId">股票代码</label>
              <input
                id="stockId"
                type="text"
                value={stockId}
                onChange={(e) => setStockId(e.target.value)}
                placeholder="例如: 000002.SZ"
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="strategy">策略</label>
              <select
                id="strategy"
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
              >
                <option value="historicLow">历史低点策略</option>
              </select>
            </div>
            
            <button type="submit" className="btn" disabled={loading}>
              {loading ? '扫描中...' : '开始扫描'}
            </button>
          </div>
        </form>

        {error && <div className="error">{error}</div>}
        
        {loading && <div className="loading">正在扫描股票...</div>}
        
        {result && (
          <div className="card">
            <h3>扫描结果</h3>
            <p><strong>策略:</strong> {result.strategy}</p>
            <p><strong>股票代码:</strong> {result.stock_id}</p>
            <p><strong>扫描时间:</strong> {result.scan_time}</p>
            <p><strong>投资机会数:</strong> {result.total_opportunities}</p>
            
            {result.opportunities && result.opportunities.length > 0 ? (
              <div>
                <h4>投资机会详情:</h4>
                {result.opportunities.map((opportunity, index) => (
                  <div key={index} className="card" style={{ marginTop: '1rem' }}>
                    <h5>机会 #{index + 1}</h5>
                    <p><strong>买入价格:</strong> {opportunity.buy_price}</p>
                    <p><strong>止损价格:</strong> {opportunity.stop_loss}</p>
                    <p><strong>止盈价格:</strong> {opportunity.take_profit}</p>
                    <p><strong>预期收益:</strong> {opportunity.expected_return}%</p>
                  </div>
                ))}
              </div>
            ) : (
              <p>未找到投资机会</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default StockScan;
