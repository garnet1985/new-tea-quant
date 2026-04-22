import React, { useState } from 'react';
import { fetchStockSimulate } from '../services/api';

function StockSimulate() {
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
      const data = await fetchStockSimulate(strategy, stockId);
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
        <h2>策略模拟</h2>
        <p>模拟历史低点策略的回测结果，验证策略有效性</p>
        
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
              {loading ? '模拟中...' : '开始模拟'}
            </button>
          </div>
        </form>

        {error && <div className="error">{error}</div>}
        
        {loading && <div className="loading">正在模拟策略...</div>}
        
        {result && (
          <div className="card">
            <h3>模拟结果</h3>
            <p><strong>策略:</strong> {result.strategy}</p>
            <p><strong>股票代码:</strong> {result.stock_id}</p>
            <p><strong>模拟结果:</strong> {result.simulation_result}</p>
            
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
              <h4>模拟说明:</h4>
              <p>此功能将模拟历史低点策略在指定股票上的表现，包括：</p>
              <ul>
                <li>历史投资机会识别</li>
                <li>买入卖出时机</li>
                <li>收益率计算</li>
                <li>风险分析</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default StockSimulate;
