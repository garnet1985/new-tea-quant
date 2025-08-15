import React, { useState, useEffect, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchStockKline, fetchStockHLAnalysis } from '../services/api';

function StockChart() {
  
  const [stockId, setStockId] = useState('000002.SZ');
  const [klineData, setKlineData] = useState(null);
  const [hlData, setHlData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const chartRef = useRef(null);

  // 获取K线数据
  const fetchKlineData = async () => {
    try {
      const data = await fetchStockKline(stockId, 'daily');
      setKlineData(data);
    } catch (err) {
      setError(`获取K线数据失败: ${err.message}`);
    }
  };

  // 获取HL分析数据
  const fetchHLData = async () => {
    try {
      console.log('开始获取HL分析数据...');
      const data = await fetchStockHLAnalysis(stockId);
      console.log('获取到HL分析数据:', data);
      setHlData(data);
    } catch (err) {
      console.error('获取HL分析数据失败:', err);
      setError(`获取HL分析数据失败: ${err.message}`);
    }
  };

  // 加载数据
  const handleLoadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('开始加载数据...');
      console.log('获取K线数据...');
      await fetchKlineData();
      console.log('获取HL分析数据...');
      await fetchHLData();
      console.log('数据加载完成');
    } catch (err) {
      console.error('数据加载失败:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 生成ECharts配置
  const getChartOption = () => {
    if (!klineData || !klineData.klines) {
      return {};
    }

    const klines = klineData.klines;
    
    // 准备K线数据 - 使用复权后的价格（不是raw字段）
    const data = klines.map(item => [
      parseFloat(item.open) || 0,      // 复权后的开盘价
      parseFloat(item.close) || 0,     // 复权后的收盘价
      parseFloat(item.lowest) || 0,    // 复权后的最低价
      parseFloat(item.highest) || 0,   // 复权后的最高价
      parseInt(item.volume) || 0       // 成交量
    ]);

    // 准备日期数据
    const dates = klines.map(item => item.date);

    // 准备投资点位数据
    const buyPoints = [];      // 买入点（蓝色）
    const sellWinPoints = [];  // 卖出盈利点（绿色）
    const sellLossPoints = []; // 卖出亏损点（红色）
    const referencePoints = []; // 历史低点（紫色菱形）

    if (hlData) {
      console.log('处理HL数据:', hlData);
      
      // 处理成功投资
      hlData.success_investments?.forEach(inv => {
        console.log('处理成功投资:', inv);
        if (inv.buy_date && inv.buy_price) {
          buyPoints.push([inv.buy_date, inv.buy_price]);
        }
        if (inv.sell_date && inv.sell_price) {
          sellWinPoints.push([inv.sell_date, inv.sell_price]);
        }
      });

      // 处理失败投资
      hlData.fail_investments?.forEach(inv => {
        console.log('处理失败投资:', inv);
        if (inv.buy_date && inv.buy_price) {
          buyPoints.push([inv.buy_date, inv.buy_price]);
        }
        if (inv.sell_date && inv.sell_price) {
          sellLossPoints.push([inv.sell_date, inv.sell_price]);
        }
      });

      // 处理开放投资
      hlData.open_investments?.forEach(inv => {
        console.log('处理开放投资:', inv);
        if (inv.buy_date && inv.buy_price) {
          buyPoints.push([inv.buy_date, inv.buy_price]);
        }
      });

      // 处理参考点位（历史低点）
      [...(hlData.success_investments || []), ...(hlData.fail_investments || []), ...(hlData.open_investments || [])].forEach(inv => {
        if (inv.historic_low_ref?.date && inv.historic_low_ref?.lowest_price) {
          referencePoints.push([inv.historic_low_ref.date, inv.historic_low_ref.lowest_price]);
        }
      });
      
      console.log('生成的投资点位:', { buyPoints, sellWinPoints, sellLossPoints, referencePoints });
    } else {
      console.log('没有HL数据');
    }

    return {
      title: {
        text: `${stockId} K线图与投资点位`,
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: function (params) {
          let result = '';
          params.forEach(param => {
            if (param.seriesType === 'candlestick') {
              result += `${param.name}<br/>
                        开盘: ${param.data[0]}<br/>
                        收盘: ${param.data[1]}<br/>
                        最低: ${param.data[2]}<br/>
                        最高: ${param.data[3]}<br/>
                        成交量: ${param.data[4]}<br/>`;
            } else if (param.seriesType === 'scatter') {
              if (param.seriesName === '买入点') {
                result += `${param.seriesName}: ${param.data[1]}<br/>`;
              } else if (param.seriesName === '卖出盈利') {
                result += `${param.seriesName}: ${param.data[1]}<br/>`;
              } else if (param.seriesName === '卖出亏损') {
                result += `${param.seriesName}: ${param.data[1]}<br/>`;
              } else if (param.seriesName === '历史低点') {
                result += `${param.seriesName}: ${param.data[1]}<br/>`;
              }
            }
          });
          return result;
        }
      },
      legend: {
        data: ['K线', '买入点', '卖出盈利', '卖出亏损', '历史低点'],
        top: 30
      },
      grid: {
        left: '10%',
        right: '10%',
        bottom: '15%'
      },
      xAxis: {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      yAxis: {
        scale: true,
        splitArea: {
          show: true
        }
      },
      dataZoom: [
        {
          type: 'inside',
          start: 50,
          end: 100
        },
        {
          show: true,
          type: 'slider',
          top: '90%',
          start: 50,
          end: 100
        }
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: data,
          itemStyle: {
            color: '#fd1050',
            color0: '#0cf49b',
            borderColor: '#fd1050',
            borderColor0: '#0cf49b'
          }
        },
        {
          name: '买入点',
          type: 'scatter',
          data: buyPoints,
          symbolSize: 10,
          itemStyle: {
            color: '#1890ff'
          }
        },
        {
          name: '卖出盈利',
          type: 'scatter',
          data: sellWinPoints,
          symbolSize: 10,
          itemStyle: {
            color: '#52c41a'
          }
        },
        {
          name: '卖出亏损',
          type: 'scatter',
          data: sellLossPoints,
          symbolSize: 10,
          itemStyle: {
            color: '#ff4d4f'
          }
        },
        {
          name: '历史低点',
          type: 'scatter',
          data: referencePoints,
          symbolSize: 12,
          symbol: 'diamond',
          itemStyle: {
            color: '#722ed1'
          }
        }
      ]
    };
  };

  return (
    <div className="page">
      <div className="card">
        <h2>股票K线图与投资点位</h2>
        
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'end' }}>
            <div className="form-group" style={{ flex: 1 }}>
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
            
            <button 
              onClick={handleLoadData} 
              className="btn" 
              disabled={loading}
            >
              {loading ? '加载中...' : '加载数据'}
            </button>
          </div>
        </div>

        {error && <div className="error">{error}</div>}
        
        {loading && <div className="loading">正在加载数据...</div>}
        
        {klineData && hlData && (
          <div className="card">
            <h3>分析结果</h3>
            <p><strong>股票代码:</strong> {stockId}</p>
            <p><strong>K线记录数:</strong> {klineData.total_records}</p>
            <p><strong>成功投资:</strong> {hlData.success_investments?.length || 0}</p>
            <p><strong>失败投资:</strong> {hlData.fail_investments?.length || 0}</p>
            <p><strong>开放投资:</strong> {hlData.open_investments?.length || 0}</p>
            
            <div style={{ marginTop: '2rem' }}>
              <ReactECharts
                ref={chartRef}
                option={getChartOption()}
                style={{ height: '600px', width: '100%' }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default StockChart;
