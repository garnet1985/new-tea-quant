import React from 'react';
import { Link } from 'react-router-dom';

function Home() {
  return (
    <div className="page">
      <div className="card">
        <h2>欢迎使用股票分析系统</h2>
        <p>这是一个基于历史低点策略的股票分析工具，提供以下功能：</p>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginTop: '2rem' }}>
          <div className="card">
            <h3>📊 K线数据</h3>
            <p>查看股票的日K线和月K线数据，支持前复权显示</p>
            <Link to="/kline" className="btn">查看K线</Link>
          </div>
          
          <div className="card">
            <h3>🎯 策略扫描</h3>
            <p>使用历史低点策略扫描股票，寻找投资机会</p>
            <Link to="/scan" className="btn">开始扫描</Link>
          </div>
          
          <div className="card">
            <h3>📈 策略模拟</h3>
            <p>模拟历史低点策略的回测结果，验证策略有效性</p>
            <Link to="/simulate" className="btn">开始模拟</Link>
          </div>
        </div>
        
        <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
          <h4>系统特点：</h4>
          <ul>
            <li>基于历史低点的投资策略</li>
            <li>支持多种时间周期分析</li>
            <li>实时数据更新</li>
            <li>策略回测和模拟</li>
            <li>投资记录和统计</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Home;
