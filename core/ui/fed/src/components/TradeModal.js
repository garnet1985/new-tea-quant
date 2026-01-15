import React, { useState, useEffect } from 'react';
import StockAutocomplete from './StockAutocomplete';

function TradeModal({ trade, onClose, onSave, isEdit, holding }) {
  const [formData, setFormData] = useState({
    stock_id: trade?.stock_id || '',
    strategy: trade?.strategy || '',
    note: trade?.note || '',
    // 首次买入信息（仅用于新建）
    first_buy_price: '',
    first_buy_amount: '',
    first_buy_date: new Date().toISOString().split('T')[0]
  });
  const [strategies, setStrategies] = useState([]);
  
  useEffect(() => {
    loadStrategies();
  }, []);
  
  const loadStrategies = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/investment/strategies');
      const data = await response.json();
      if (data.success) {
        setStrategies(data.data || []);
      }
    } catch (err) {
      console.error('加载策略列表失败:', err);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h2>{isEdit ? '编辑交易' : '创建交易'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>股票代码</label>
            <StockAutocomplete
              value={formData.stock_id}
              onChange={(value) => setFormData({ ...formData, stock_id: value })}
              disabled={isEdit}
              autoSearch={!isEdit}
            />
          </div>
          <div className="form-group">
            <label>策略</label>
            <select
              name="strategy"
              value={formData.strategy}
              onChange={handleChange}
            >
              <option value="">请选择策略</option>
              {strategies.map(strategy => (
                <option key={strategy.key} value={strategy.key}>
                  {strategy.name} ({strategy.key})
                </option>
              ))}
            </select>
          </div>
          
          {isEdit && holding && (
            <div className="form-group" style={{ backgroundColor: '#f9f9f9', padding: '15px', borderRadius: '4px' }}>
              <h3 style={{ marginTop: 0, fontSize: '16px', fontWeight: 'bold', marginBottom: '10px' }}>首次买入信息</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ color: '#666', fontSize: '14px' }}>日期：</label>
                  <span style={{ color: '#333' }}>{holding.first_buy_date || '-'}</span>
                </div>
                <div>
                  <label style={{ color: '#666', fontSize: '14px' }}>价格：</label>
                  <span style={{ color: '#333' }}>{holding.first_buy_price ? `¥${holding.first_buy_price}` : '-'}</span>
                </div>
              </div>
              <div style={{ marginTop: '10px' }}>
                <label style={{ color: '#666', fontSize: '14px' }}>当前持仓：</label>
                <span style={{ color: '#333' }}>{holding.amount || 0} 股</span>
              </div>
              <div style={{ marginTop: '5px' }}>
                <label style={{ color: '#666', fontSize: '14px' }}>平均成本：</label>
                <span style={{ color: '#333' }}>{holding.avg_cost ? `¥${holding.avg_cost}` : '-'}</span>
              </div>
            </div>
          )}
          
          {!isEdit && (
            <>
              <div className="form-group">
                <label>首次买入日期</label>
                <input
                  type="date"
                  name="first_buy_date"
                  value={formData.first_buy_date}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>首次买入价格</label>
                <input
                  type="number"
                  step="0.01"
                  name="first_buy_price"
                  value={formData.first_buy_price}
                  onChange={handleChange}
                  placeholder="例如: 10.50"
                  required
                />
              </div>
              <div className="form-group">
                <label>首次买入数量 (股)</label>
                <input
                  type="number"
                  step="1"
                  name="first_buy_amount"
                  value={formData.first_buy_amount}
                  onChange={handleChange}
                  placeholder="例如: 1000"
                  required
                />
              </div>
            </>
          )}
          <div className="form-group">
            <label>备注</label>
            <textarea
              name="note"
              value={formData.note}
              onChange={handleChange}
              rows="3"
              placeholder="可选"
              style={{ width: '100%' }}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              取消
            </button>
            <button type="submit" className="btn">
              保存
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default TradeModal;

