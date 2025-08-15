import React, { useState } from 'react';
import { fetchStockKline } from '../services/api';
import KlineChart from '../components/KlineChart';
import SimpleChart from '../components/SimpleChart';

function StockKline() {
  alert('StockKline组件被渲染');
  
  const [stockId, setStockId] = useState('000002.SZ');
  const [term, setTerm] = useState('daily');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const result = await fetchStockKline(stockId, term);
      alert('数据获取成功，数据条数: ' + (result.klines ? result.klines.length : 0));
      setData(result);
    } catch (err) {
      alert('数据获取失败: ' + err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <h2>股票K线数据</h2>
        
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
              <label htmlFor="term">K线周期</label>
              <select
                id="term"
                value={term}
                onChange={(e) => setTerm(e.target.value)}
              >
                <option value="daily">日K线</option>
                <option value="monthly">月K线</option>
              </select>
            </div>
            
            <button type="submit" className="btn" disabled={loading}>
              {loading ? '加载中...' : '获取数据'}
            </button>
          </div>
        </form>

        {error && <div className="error">{error}</div>}
        
        {loading && <div className="loading">正在加载数据...</div>}
        
        {data && (
          <div className="card">
            <h3>数据结果</h3>
            <p><strong>股票代码:</strong> {data.stock_id}</p>
            <p><strong>周期:</strong> {data.term}</p>
            <p><strong>记录数:</strong> {data.total_records}</p>
            
                        {data.klines && data.klines.length > 0 && (
              <div>
                <h4>测试图表:</h4>
                <SimpleChart />
                
                <h4>K线图:</h4>
                <KlineChart data={data} stockId={stockId} />
                
                <h4 style={{ marginTop: '2rem' }}>最新5条记录:</h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>日期</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>开盘</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>最高</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>最低</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>收盘</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>成交量</th>
                        <th style={{ border: '1px solid #ddd', padding: '8px' }}>成交额</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.klines.slice(-5).map((kline, index) => (
                        <tr key={index}>
                          <td style={{ border: '1px solid #ddd', padding: '8px' }}>{kline.date}</td>
                          <td style={{ border: '1px solid #ddd', padding: '8px' }}>{kline.open}</td>
                          <td style={{ border: '1px solid #ddd', padding: '8px' }}>{kline.highest}</td>
                          <td style={{ border: '1px solid #ddd', padding: '8px' }}>{kline.lowest}</td>
                          <td style={{ border: '1px solid #ddd', padding: '8px' }}>{kline.close}</td>
                          <td style={{ border: '1px solid #ddd', padding: '8px' }}>{kline.volume}</td>
                          <td style={{ border: '1px solid #ddd', padding: '8px' }}>{kline.amount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default StockKline;
