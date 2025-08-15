import React, { useState, useEffect, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchStockKline, fetchStockHLAnalysis } from '../services/api';

function StockChart() {
  
  const [stockId, setStockId] = useState('000002.SZ');
  const [klineData, setKlineData] = useState(null);
  const [hlData, setHlData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pointDetails, setPointDetails] = useState(new Map());
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
      const data = await fetchStockHLAnalysis(stockId);
      setHlData(data);
      
      // 更新点位详细信息
      updatePointDetails(data);
    } catch (err) {
      console.error('获取HL分析数据失败:', err);
      setError(`获取HL分析数据失败: ${err.message}`);
    }
  };

  // 更新点位详细信息
  const updatePointDetails = (hlData) => {
    const newPointDetails = new Map();
    
    if (hlData && hlData.data) {
      const stockData = hlData.data;
      const results = stockData.results || [];
      
      // 处理所有投资记录
      results.forEach(result => {
        const investmentInfo = result.investment_info || {};
        const settlementInfo = result.settlement_info || {};
        
        // 买入点
        if (investmentInfo.start_date && investmentInfo.purchase_price) {
          const pointKey = `buy_${investmentInfo.start_date}`;
          newPointDetails.set(pointKey, {
            type: 'buy',
            date: investmentInfo.start_date,
            price: investmentInfo.purchase_price,
            target_win: investmentInfo.target_win,
            target_loss: investmentInfo.target_loss,
            stock_name: stockData.stock_info?.name || 'Unknown'
          });
        }
        
        // 卖出点（如果有结算信息）
        if (settlementInfo.exit_date && settlementInfo.exit_price) {
          const pointKey = `sell_${settlementInfo.exit_date}`;
          newPointDetails.set(pointKey, {
            type: result.status === 'win' ? 'sell_win' : 'sell_loss',
            date: settlementInfo.exit_date,
            price: settlementInfo.exit_price,
            stock_name: stockData.stock_info?.name || 'Unknown'
          });
        }
        
        // 历史低点参考
        if (investmentInfo.historic_low_ref?.date && investmentInfo.historic_low_ref?.lowest_price) {
          const pointKey = `ref_${investmentInfo.historic_low_ref.date}`;
          newPointDetails.set(pointKey, {
            type: 'reference',
            date: investmentInfo.historic_low_ref.date,
            price: investmentInfo.historic_low_ref.lowest_price,
            ref_price_7p: investmentInfo.historic_low_ref.lowest_price * 1.07, // 上7%
            stock_name: stockData.stock_info?.name || 'Unknown'
          });
        }
      });
    }
    
    setPointDetails(newPointDetails);
  };

  // 加载数据
  const handleLoadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await fetchKlineData();
      await fetchHLData();
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



    if (hlData && hlData.data) {
      const stockData = hlData.data;
      const results = stockData.results || [];
      
      // 处理所有投资记录
      results.forEach(result => {
        const investmentInfo = result.investment_info || {};
        const settlementInfo = result.settlement_info || {};
        
        // 买入点
        if (investmentInfo.start_date && investmentInfo.purchase_price) {
          buyPoints.push([investmentInfo.start_date, investmentInfo.purchase_price]);
        }
        
        // 卖出点
        if (settlementInfo.exit_date && settlementInfo.exit_price) {
          if (result.status === 'win') {
            sellWinPoints.push([settlementInfo.exit_date, settlementInfo.exit_price]);
          } else if (result.status === 'loss') {
            sellLossPoints.push([settlementInfo.exit_date, settlementInfo.exit_price]);
          }
        }
        
        // 历史低点参考
        if (investmentInfo.historic_low_ref?.date && investmentInfo.historic_low_ref?.lowest_price) {
          referencePoints.push([investmentInfo.historic_low_ref.date, investmentInfo.historic_low_ref.lowest_price]);
        }
      });
    } else {
      // 没有HL数据
    }

    const option = {
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
        data: ['K线', '止损线', '止盈线', '买入点', '卖出盈利', '卖出亏损', '历史低点'],
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
        // 辅助线系列（动态显示）
        {
          name: '辅助线',
          type: 'line',
          data: [],
          lineStyle: {
            color: '#ffa500',
            width: 2,
            type: 'dashed'
          },
          symbol: 'none',
          silent: true
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

    return option;
  };

  return (
    <div className="page page-chart">
      <div className="card">
        <div className="card-header container">
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
              
              <button 
                onClick={() => {
                  if (chartRef.current) {
                    chartRef.current.getEchartsInstance().setOption(getChartOption());
                  }
                }} 
                className="btn" 
                style={{ backgroundColor: '#ff4d4f' }}
              >
                清除辅助线
              </button>
            </div>
          </div>
          {error && <div className="error">{error}</div>}
          {loading && <div className="loading">正在加载数据...</div>}
        </div>
        
        
        
        {klineData && hlData && (
          <div className="card">
            <h3>分析结果</h3>
            <p><strong>股票代码:</strong> {stockId}</p>
            <p><strong>K线记录数:</strong> {klineData.total_records}</p>
            <p><strong>成功投资:</strong> {hlData.success_investments?.length || 0}</p>
            <p><strong>失败投资:</strong> {hlData.fail_investments?.length || 0}</p>
            <p><strong>开放投资:</strong> {hlData.open_investments?.length || 0}</p>
            
            <div style={{ height: '600px', marginTop: '2rem' }}>
              <ReactECharts
                ref={chartRef}
                option={getChartOption()}
                style={{ height: '100%' }}
                onEvents={{
                  click: (params) => {
                    if (params.seriesType === 'scatter') {
                      const pointDate = params.data[0];
                      const pointPrice = params.data[1];
                      

                      
                      // 查找对应的点位信息
                      let pointInfo = null;
                      for (const [key, info] of pointDetails.entries()) {
                        if (info.date === pointDate && Math.abs(info.price - pointPrice) < 0.01) {
                          pointInfo = info;
                          break;
                        }
                      }
                      
                      if (pointInfo) {
                        // 根据点位类型显示不同的辅助线
                        if (pointInfo.type === 'buy' && pointInfo.target_win && pointInfo.target_loss) {
                          
                          // 买入点：显示止损止盈横线
                          const stopLossData = [
                            [pointInfo.date, pointInfo.target_loss], // 止损价格横线起点
                            [pointInfo.date, pointInfo.target_loss]   // 止损价格横线终点
                          ];
                          const takeProfitData = [
                            [pointInfo.date, pointInfo.target_win],  // 止盈价格横线起点
                            [pointInfo.date, pointInfo.target_win]   // 止盈价格横线终点
                          ];
                          

                          
                          const newOption = {
                            ...getChartOption(),
                            series: [
                              ...getChartOption().series.slice(0, 1), // K线
                              ...getChartOption().series.slice(2) // 其他点位
                            ]
                          };
                          
                          // 为K线系列添加markLine
                          newOption.series[0].markLine = {
                            silent: true,
                            symbol: 'none',
                            lineStyle: {
                              color: '#ff4d4f',
                              width: 3,
                              type: 'dashed'
                            },
                            data: [
                              {
                                yAxis: pointInfo.target_loss,
                                name: '止损线'
                              },
                              {
                                yAxis: pointInfo.target_win,
                                name: '止盈线',
                                lineStyle: {
                                  color: '#52c41a',
                                  width: 3,
                                  type: 'dashed'
                                }
                              },
                              // 添加当前点位线
                              {
                                yAxis: pointInfo.price,
                                name: '当前点位',
                                lineStyle: {
                                  color: '#1890ff',
                                  width: 2,
                                  type: 'dashed'
                                }
                              }
                            ]
                          };
                          
                          if (chartRef.current) {
                            const chart = chartRef.current.getEchartsInstance();
                            chart.setOption(newOption);
                          }
                        } else if (pointInfo.type === 'reference') {

                          
                          // 历史低点：显示上7%横线
                          const refLineData = [
                            [pointInfo.date, pointInfo.ref_price_7p], // 上7%价格横线起点
                            [pointInfo.date, pointInfo.ref_price_7p]  // 上7%价格横线终点
                          ];
                          

                          
                          const newOption = {
                            ...getChartOption(),
                            series: [
                              ...getChartOption().series.slice(0, 1), // K线
                              ...getChartOption().series.slice(2) // 其他点位
                            ]
                          };
                          
                          // 为K线系列添加markLine
                          newOption.series[0].markLine = {
                            silent: true,
                            symbol: 'none',
                            lineStyle: {
                              color: '#722ed1',
                              width: 3,
                              type: 'dashed'
                            },
                            data: [
                              {
                                yAxis: pointInfo.ref_price_7p,
                                name: '上7%线'
                              },
                              // 添加当前点位线
                              {
                                yAxis: pointInfo.price,
                                name: '当前点位',
                                lineStyle: {
                                  color: '#1890ff',
                                  width: 2,
                                  type: 'dashed'
                                }
                              }
                            ]
                          };
                          
                          if (chartRef.current) {
                            const chart = chartRef.current.getEchartsInstance();
                            chart.setOption(newOption);
                          }
                        }
                      } else {

                      }
                    }
                  },
                  dblclick: (params) => {
                    // 双击清除辅助线
                                      if (chartRef.current) {
                    chartRef.current.getEchartsInstance().setOption(getChartOption());
                  }
                  }
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default StockChart;
