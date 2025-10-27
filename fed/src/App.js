import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Home from './pages/Home';
import StockKline from './pages/StockKline';
import StockScan from './pages/StockScan';
import StockSimulate from './pages/StockSimulate';
import StockChart from './pages/StockChart';
import Investment from './pages/Investment';

// 导航组件
function Navigation() {
  const location = useLocation();
  
  return (
    <nav className="nav">
      <div className="container">
        <div className="nav-content">
          <h1>股票分析系统</h1>
          <div className="nav-links">
            <Link to="/" className={location.pathname === '/' ? 'active' : ''}>
              首页
            </Link>
            <Link to="/kline" className={location.pathname === '/kline' ? 'active' : ''}>
              K线数据
            </Link>
            <Link to="/scan" className={location.pathname === '/scan' ? 'active' : ''}>
              策略扫描
            </Link>
            <Link to="/simulate" className={location.pathname === '/simulate' ? 'active' : ''}>
              策略模拟
            </Link>
            <Link to="/chart" className={location.pathname === '/chart' ? 'active' : ''}>
              K线图
            </Link>
            <Link to="/investment" className={location.pathname === '/investment' ? 'active' : ''}>
              投资管理
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="App">
        <Navigation />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/kline" element={<StockKline />} />
            <Route path="/scan" element={<StockScan />} />
            <Route path="/simulate" element={<StockSimulate />} />
            <Route path="/chart" element={<StockChart />} />
            <Route path="/investment" element={<Investment />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
