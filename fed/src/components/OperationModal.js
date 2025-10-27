import React, { useState } from 'react';

function OperationModal({ tradeId, onClose, onSave, minDate, maxDate }) {
  const normalizeDate = (dateStr) => {
    if (!dateStr) return null;
    if (dateStr.includes(',')) {
      return new Date(dateStr).toISOString().split('T')[0];
    }
    return dateStr.split('T')[0].split(' ')[0];
  };
  
  const normalizedMinDate = minDate ? normalizeDate(minDate) : null;
  const normalizedMaxDate = maxDate ? normalizeDate(maxDate) : null;
  
  const [formData, setFormData] = useState({
    type: 'buy',
    date: new Date().toISOString().split('T')[0],
    price: '',
    amount: '',
    note: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // 日期验证
    if (normalizedMinDate && formData.date < normalizedMinDate) {
      alert(`操作日期不能早于首次买入日期: ${normalizedMinDate}`);
      return;
    }
    if (normalizedMaxDate && formData.date > normalizedMaxDate) {
      alert('操作日期不能是未来日期');
      return;
    }
    
    // 数据类型转换
    const data = {
      ...formData,
      price: parseFloat(formData.price),
      amount: parseInt(formData.amount)
    };
    
    onSave(data, normalizedMinDate, normalizedMaxDate);
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
          <h2>添加操作</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>操作类型</label>
            <select name="type" value={formData.type} onChange={handleChange} required>
              <option value="buy">买入</option>
              <option value="sell">卖出</option>
            </select>
          </div>
          <div className="form-group">
            <label>日期</label>
            <input
              type="date"
              name="date"
              value={formData.date}
              onChange={handleChange}
              min={normalizedMinDate}
              max={normalizedMaxDate}
              required
            />
            {normalizedMinDate && (
              <small style={{ color: '#666', display: 'block', marginTop: '4px' }}>
                最早日期: {normalizedMinDate}
              </small>
            )}
          </div>
          <div className="form-group">
            <label>价格</label>
            <input
              type="number"
              name="price"
              value={formData.price}
              onChange={handleChange}
              required
              step="0.01"
              placeholder="例: 10.50"
            />
          </div>
          <div className="form-group">
            <label>数量（股）</label>
            <input
              type="number"
              name="amount"
              value={formData.amount}
              onChange={handleChange}
              required
              step="100"
              placeholder="例: 1000"
            />
          </div>
          <div className="form-group">
            <label>备注</label>
            <textarea
              name="note"
              value={formData.note}
              onChange={handleChange}
              rows="3"
              placeholder="可选"
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

export default OperationModal;

