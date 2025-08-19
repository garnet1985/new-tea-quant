// API服务 - 与后端BFF API通信

const API_BASE_URL = 'http://localhost:5001';

// 通用请求函数
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || '请求失败');
    }

    return data.data;
  } catch (error) {
    console.error('API请求失败:', error);
    throw error;
  }
}

// 获取股票K线数据
export async function fetchStockKline(stockId, term = 'daily') {
  return apiRequest(`/api/stock/kline/${stockId}/${term}`);
}

// 获取股票策略扫描结果
export async function fetchStockScan(strategy, stockId) {
  return apiRequest(`/api/stock/scan/${strategy}/${stockId}`);
}

// 获取股票策略模拟结果
export async function fetchStockSimulate(strategy, stockId) {
  return apiRequest(`/api/stock/simulate/${strategy}/${stockId}`);
}

// 获取股票HL策略分析结果
export async function fetchStockHLAnalysis(stockId) {
  return apiRequest(`/api/stock/hl-analysis/${stockId}`);
}

// 获取股票所有计算出的历史低点
export async function fetchStockAllHistoricLows(stockId) {
  return apiRequest(`/api/stock/all-historic-lows/${stockId}`);
}

// 健康检查
export async function healthCheck() {
  return apiRequest('/api/health');
}
